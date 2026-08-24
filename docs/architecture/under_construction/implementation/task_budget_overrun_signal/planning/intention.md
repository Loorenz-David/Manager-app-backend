# Intention: Task Budget Overrun Signal (one batched verdict read for the managers task list)

```
status: **RATIFIED** (round 10, 2026-08-24) — re-ratified by the owner (**David**) on
        2026-08-24, on the re-ratification surface at **§10.6**. The owner answered
        **"yes"** after that surface was relayed: D9's forecast-versus-incurred
        distinction, D10's no-work-ahead guard, the production-time convergence caveat,
        and the four non-visible contract resolutions. This restores the pipeline's
        strongest gate: mechanism-inventory has passed and implementation-planning may
        now begin. The round-5 ratification remains historical authority; it was not
        withdrawn or re-litigated.
        Prior header, superseded — **COLLABORATING** (round 8, 2026-08-24): every owner
        decision was answered but re-ratification on §10.6 remained outstanding. The
        gate had re-opened in round 6
        on a material contradiction inside the ratified text: §6 claimed a zero-worked
        `INFEASIBLE` task was `within_budget` while §6's own next bullet served
        `allowed_seconds` unclamped, so §5.1 subtracted a negative pot and reported a
        red badge with real money on a task nobody had touched (measured, §12A P9).
        **The owner ruled with a third reading neither offered branch carried** (§10.4,
        verbatim): a negative pot before any work is a **forecast**, not a fact —
        the price was set before the work began, so the task is *already projected* to
        go over; it becomes a **fact** the moment someone starts working it. Folded as
        §6A.3 and into §5.1, §5.2, §6, §3.4 and §3A.4.
        **What the ruling did not touch, so nothing is re-litigated: D1 stands**
        (the projection's operand is still the unclamped task pot), **the §1A
        measurement ledger stands unchanged** — all six outcomes read exactly as
        ratified in round 5 — and **D2 stands and is now literally true** for the first
        time. **Re-ratification is therefore scoped to the folded text of D9 and D10,
        the §2.4A convergence caveat, and the four unilateral resolutions of §10.4.**
        **D10 (round 8):** no work left to come ⇒ no forecast — skipped-out steps add no
        time, so no overrun and no projection; work still ahead keeps the forecast.
        Round 8 also **corrected round 7's own card**, which had named
        `remaining_commitment > 0` as the mechanism: derived from the real allocator that
        sum is identically zero on every infeasible task and would have deleted D9's
        verdict (§11 R8-a/R8-b, §12A P12).
        (The superseded header correctly held all downstream prompts until this act.)
        **Round 5's ratification is not withdrawn and is not re-litigated.** D4–D8
        stand exactly as recorded (§10.2, §10.3). Everything round 6 added beyond D9 is
        **contract, not semantics**: §§3A, 4A, 5A, 6A, 7A deepen §§3–7 without changing
        any meaning they already carried. The **re-ratification surface** — every
        sentence that changed since the owner's round-5 act, and nothing else — is at
        **§10.6**.
        Prior header, superseded — **RATIFIED** (round 5, 2026-08-24), ratified by the
        owner (**David**) on the ratification surface written at **§10.1**: the
        intended outcome in plain language, the **§1A measurement ledger verbatim (all
        six entries, M1–M6)**, the §8 scope boundaries, and the decision index (D1–D3
        settled, none outstanding). Before the act, the owner explicitly confirmed four
        calls the document had made on the owner's behalf — **D5–D8** (§10.3) — and
        answered "**Yes — ratify as presented**." Recorded in §11 round 5.
        **⚠ Section-letter precedence:** §3.4 supersedes its own round-1 wording — a
        second, independent cause of the divergence was found in round 2. §11 R4-b
        supersedes R3-c. **§11 R4-c is RESOLVED by D5** (§10.3): HC-2 stands; the
        worker time-pressure handoff is a separate project. **§§3A/4A/5A/6A/7A (round
        6) are contract grade: where they and §§3–7 differ in *precision*, the lettered
        section governs; where they differ in *meaning*, the numbered section governs
        and the lettered one is a defect. §6A.3 is RESOLVED by D9 and the §3.3 / §6 rank-3
        conjunct by D10; **nothing in this document is marked OPEN.** §2.4A (round 8)
        qualifies §2.4's convergence promise.**
        Prior header, superseded: READY_FOR_RATIFICATION (round 4) — shaper's claim,
        0 owner decisions open, D4 outstanding.
role: intention (pipeline root artifact)
shaped_from: docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md
             (the frontend's request, authored by the frontend's Claude Opus 5 agent)
             plus owner decisions taken in the shaping conversation of 2026-08-24
             (S1–S3 round 1; D1–D2 round 2; D3 round 3; R4-a round 4; D4–D8 round 5; §11),
             the mechanism contracts of round 6 (§§3A–7A), D9 of round 7 (§10.4) and
             D10 of round 8 (§10.5).
date: 2026-08-24
round: 10
```

---

## 1. Objective & hard constraints

**One batched, read-only endpoint** that answers a single question per task — *is this
task over its production budget, is it heading there, and what does that cost* — as a
**served verdict**, so the managers task list renders a value instead of computing one.

Today the list fetches a full per-step allocation payload (~1,350 serialized values for
a 25-task page) to render two numbers per task, and the amber "projected to go over"
half of the design cannot be built from that payload at all, because it does not carry
section rows or step lifecycle state. The projection rule therefore lives in the
frontend, as `buildOutlook`. This pipeline moves the rule into the domain that owns the
arithmetic and publishes its verdict.

**Hard constraints:**

- **HC-1 — Read-only, derive-on-read.** No new table, no migration, no persisted
  derived value, no worker, no event, no socket. Consequence: `CALCULATION_VERSION`
  (`calculator.py:20`) is **not** bumped — its contract covers persisted formula
  outputs and this feature persists nothing. Same reasoning as
  `simple_valuation_editor` HC-1 and `simple_production_budget_division` HC-2.
- **HC-2 — Additive only.** One new pure domain module, one new query service, one new
  serializer function, one new route. **No change to `budget-allocations`,
  `production-time`, `budget-status`, `price-scenario`, `divide_production_budget`, or
  any published contract in `Application_contracts`.** The workers-app step cards read
  `budget-allocations` per-step and are correct today; this is an additive sibling, not
  a replacement. Deleting this feature must leave zero residue.
  - **HC-2a — enumerated exception.** Mounting a new item-economics route trips the v1
    route-mirror tripwires by design. Exactly **four** artifacts change, by addition
    only, each reverted by one edit:
    1. `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` —
       `_EXPECTED_ROUTES` (+1 row, `:33`) and both count assertions **26 → 27**
       (`:127`, `:128`);
    2. `app/beyo_manager/routers/README.md` — one Quick Index row and one detail
       section (the mirror test asserts README rows equal the route set, `:115`);
    3. `app/tests/unit/routers/api_v1/test_item_economics_router.py` — `_ROUTES`
       (`:14`) and **not** `_ALL_ROLE_ROUTES` (`:49`), because this route is
       manager-gated (HC-3);
    4. the router module `app/beyo_manager/routers/api_v1/item_economics.py`.

    No other v1 artifact may change.
- **HC-3 — Money audience: ADMIN and MANAGER only.** The row carries three monetary
  fields. The standing decision `decision-money-audience-admin-manager-only`
  (architecture graph) governs: monetary fields are served to ADMIN and MANAGER
  identities only, WORKER and SELLER excluded in every payload family, and **a
  withheld monetary key is ABSENT, never null**. The frontend offered "WORKER/SELLER
  only if free" — it is not free: a worker variant would have to drop three keys,
  which contradicts HC-4's flat non-nullable row and would need a second serializer.
  **There is no worker or seller variant of this endpoint in v1.** (Resolved in
  shaping, §11 S4; the shipped consumer is the managers app.)
- **HC-4 — Every field non-nullable, with an explicit default.** `0` for the integers,
  an explicit enum member for the states, and `no_budget` is a **state, not an
  absence**. The frontend states that a `.nullable()` field the backend later stopped
  sending has taken it down twice. `budget_state` carries every distinction a null
  would.
- **HC-5 — The verdict is served, never recomputed by the client.** The frontend
  renders `budget_state` on receipt and may only extrapolate the time-dependent
  figures forward between polls; every fresh payload re-anchors the baseline. This is
  the pattern `HANDOFF_TO_BACKEND_production_time_live_budget_clock_20260819.md` §5
  already established and `useTaskBudgetAllocationsQuery` already implements via its
  `receivedAtMs` stamp. **No server "now" timestamp is served** — the client measures
  elapsed time from response receipt, and a server clock would reintroduce the
  comparison the live-clock pipeline removed.
- **HC-6 — Reuse the shipped rule; never re-derive it.** Three specific reuses, each
  load-bearing and each with a measured reason in §4:
  1. money goes through `calculate_consumed_cost_minor` (`calculator.py:326`) —
     **calling it, not reimplementing its arithmetic** (§4.2);
  2. the "still to come" predicate is `TERMINAL_STEP_STATES`
     (`domain/task_steps/constants.py:4`), not a locally spelled set (§3.2);
  3. the section rows come from `divide_production_budget`
     (`budget_division.py:289`), which already computes them (§3.1).
- **HC-7 — This buys payload and ownership, not query cost.** The new service reuses
  the batched loader's query shape: twelve statements per request. Response drops from
  ~1,350 values to ~225 for a 25-task page and the rule moves into the domain — both
  real. **It does not become a cheap sweep.** Any future scheduler over all open tasks
  in a workspace is a different problem with a different query shape and is explicitly
  out of scope (§8).

---

## 1A. Measurement ledger (trace-chain root)

**What an entry is.** An **observable outcome** — measurable true or false on the
shipped system — plus the **defect family it guards**. Planners' criteria may trace
only to these entries or to a mechanism contract (§3, §4). A criterion row tracing to
nothing is cut before its plan ships; an outcome missing here cannot legitimately grow
tests later — it routes back to this ledger as a candidate criterion.

**Ranked as the scope ladder is ranked:** M1–M3 are why the pipeline exists; M4–M5 are
what it must not get wrong; M6 is what it must not break.

| ID | Observable outcome | Defect family it guards | Derived from |
|---|---|---|---|
| **M1** | For a task not yet over budget whose unfinished sections' remaining targets exceed its remaining pot by at least the agreed floor, the endpoint returns `projected_over` with `projected_over_seconds > 0` — computed in the backend, from section rows the client never receives. | **The rule that lives in two places.** A projection re-implemented client-side against a payload that cannot express it, drifting from the server's arithmetic the first time either moves. This is the entire reason the frontend wrote the handoff. | §1 objective; §3; handoff "Why the projection cannot be built from that payload" |
| **M2** | `over_cost_minor` for a given task and duration equals, to the minor unit, the figure `budget-status` names for the same duration on the same task — because both are the **same function call**, not two agreeing derivations. | **Two screens naming different money for one task.** Measured, not assumed: an independently-derived exact-rational half-even disagrees with the shipped `calculate_consumed_cost_minor` on **24 of 20,005** probed cases (§4.2), all at exact half-ties. A "mathematically cleaner" reimplementation ships öre-level disagreement between this badge, the valuation editor, and any future notification. | **HC-6.1**; §4.2; handoff acceptance criterion 5 |
| **M3** | A section already past its own slice contributes **0** to the projection, never a negative — and a fixture where one section's overrun would otherwise cancel another section's real remaining work produces a signal, not silence. | **The quiet cancellation.** How far an already-overrunning section will *keep* overrunning is not knowable; letting it subtract erases a different stage's genuine remaining commitment and the task reads as fine. | §3.3; handoff acceptance criterion 6; frontend `buildOutlook` comment |
| **M4** | Every visible requested task is **present** in the response with an explicit `budget_state` — including tasks with no usable committed evaluation, which return `no_budget`. Only unknown, deleted, and other-workspace ids are omitted. The response for N tasks is N flat rows with **no nested array at any depth**. | **Silent omission read as reassurance.** A task dropped from the payload renders as no badge, which a manager reads as "within budget". Plus the shape regression the whole handoff exists to prevent: nesting creeping back in. | **HC-4**; handoff acceptance criteria 4 and 9; `budget-allocations` §1 |
| **M5** | Two calls a few seconds apart against unchanged state differ only in the time-dependent figures — never in `budget_state`, never in row membership or ordering, never in `allowed_seconds`. | **Verdict flicker.** `budget_state` is the intended future event trigger; a verdict that oscillates at a boundary becomes a notification per poll. Stability here is what makes the event tractable later, even though this pipeline ships no event. | handoff acceptance criterion 7; §7.3 |
| **M6** | No existing payload, rule, or persisted value changes: `budget-allocations`, `production-time`, `budget-status` and `price-scenario` serve byte-identical responses for identical state before and after, and the four HC-2a artifacts are the only pre-existing files touched. | **Collateral regression.** The workers-app step cards and the managers single-task surface both ride the read models this feature reuses; a "small refactor into shared code" is how they break. | **HC-2**; **HC-2a** |

**Mechanism contracts are traceable targets in their own right** (charter trace chain,
link 2). The contracts this intention carries register here against the outcome each
serves:

| Contract | Registers against |
|---|---|
| §3.1 (section rows come from the shipped allocator) | **M1**, M6 |
| §3.2 (the "still to come" predicate) | **M1** |
| §3.3 (the clamp and the noise floor) | **M3**, M1 |
| §3.4 (**the two-operand accounting divergence** — open, card 1) | **M1**, M5 |
| §4.1 (which rate: the evaluation snapshot) | **M2** |
| §4.2 (money is a call, not a formula) | **M2** |
| §5 (row shape, field ownership, defaults) | **M4** |
| §7.3 (batch semantics, cap, error identity) | **M4**, M5 |
| §3A.1 (the allocator **call** — its inputs, not only its callee) | **M1**, M6 |
| §3A.2 (the terminal predicate compares against the **value** set) | **M1** |
| §3A.3 (the complete step-state partition, all eight members) | **M1**, M3 |
| §3A.4 (clamp/floor arithmetic: types, order, boundaries) | **M3**, M1 |
| §3A.5 (both operands are second-domain `int`s, never minutes) | **M1**, M2 |
| §3A.6 (the allocator is total — no crash path this rule can take) | M1 |
| §4A.1 (Q5 call identity and its exact input types) | **M2** |
| §4A.2 (rate scaling exactness; a committed rate is never zero) | M2 |
| §4A.3 (a non-zero overrun may legitimately cost `0`) | **M2** — overclaim guard |
| §5A.1 (production types and their JSON forms, per field) | **M4** |
| §5A.2 (the `no_budget` row is **constructed**, never computed) | **M4** |
| §5A.3 (`no_currency` is wire-only — the mechanics that keep it so) | M4 |
| §6A.1 (budget-bearing ⟺ a current committed evaluation exists) | **M4** |
| §6A.2 (the seven-row state decision procedure, ties included) | **M4** |
| §6A.3 (**D9**: the negative-allowance, zero-work boundary — incurred vs forecast) | **M4** |
| §6A.4 (what M5 does and does not promise) | **M5** — overclaim guard |
| §7A.1 (cardinality, duplicates, visibility predicate) | **M4** |
| §7A.2 (deterministic row ordering) | **M5** |
| §7A.3 (error identity, envelope, and the two 422s) | M4 |
| §7A.4 (route precedence and mounting) | M6 |
| §7A.5 (the authorization boundary) | M6 |
| §7A.6 (HC-7's query-count statement, corrected) | M6 |

**What this ledger does not do**, stated so a filled trace cell is not mistaken for a
verified outcome. It makes *"was this test worth writing"* answerable. It says nothing
about whether a test tracing to **M1** can actually observe **M1** failing — that is
the criterion's job, and the row-that-cannot-fail family lives entirely inside a
correctly-traced row.

---

## 2. Grounding — what exists today (all paths read 2026-08-24, this session)

### 2.1 The four item-economics read surfaces

| Surface | Service | Shape | Roles |
|---|---|---|---|
| `GET /tasks/budget-allocations` | `get_task_budget_allocations.py` | batched, cap 50, per-**step** rows | all four |
| `GET /tasks/{id}/production-time` | `get_task_production_time.py` | one task, per-**section** rows | all four |
| `GET /tasks/{id}/budget-status` | `get_task_budget_status.py` | one task, money (manager face) | all four, worker face separate |
| `GET /tasks/{id}/price-scenario` | `get_task_price_scenario.py` | one task, money | ADMIN/MANAGER |

All four funnel through the pure allocator `divide_production_budget`
(`app/beyo_manager/domain/item_economics/budget_division.py:289`).

### 2.2 The allocator already computes what the projection needs

`divide_production_budget` returns **both** `sections` and `steps` (`:399-405`). Each
section row carries `state` (from `_governing_step`, `:180`), `left_seconds`,
`worked_seconds`, `allowance_seconds` and `share_state`.

`get_task_budget_allocations` computes both and **serializes only
`division["steps"]`** (`:311`). The frontend's reading is correct: the section rows
this feature needs are already computed per request and discarded. Nothing new has to
be invented — only emitted, and reduced to a verdict.

### 2.3 `_governing_step` makes section state meaningful

`_governing_step` (`budget_division.py:180-200`) prefers a **non-terminal** step over a
terminal one when choosing which step's state names the section. A section therefore
reports a terminal state only when **all** its steps are terminal — which is exactly
the semantics "this section will consume no more of the pot" requires. This is why the
section-level rule is sound and a step-level one would not be.

### 2.4 The frontend's rule, verified at the source

`packages/item-economics/src/lib/production-time-view-model.ts:282-317`. Its settled
set (`:244-249`) is `{completed, skipped, failed, cancelled}` — **character-for-
character the backend's `TERMINAL_STEP_STATES`**
(`app/beyo_manager/domain/task_steps/constants.py:4-9`). Its floor
(`PRODUCTION_TIME_OUTLOOK_MIN_OVERRUN_SECONDS`, `:255`) is 60 seconds.

**One finding the handoff does not mention, and it settles a decision.** The shipped
`buildOutlook` **already projects past an overrun that has already happened** — its own
test at `production-time-view-model.test.ts:241-249` passes `remainingSeconds: -600`
and asserts a 3219-second projection, commented *"the headline already says 10m over;
the forecast is the bigger number."* So the single-task surface already renders both
facts today. The owner's shaping decision to **populate both pairs** (§11 S2) therefore
matches the shipped frontend semantics exactly, and lets `production-time`'s outlook
converge onto this endpoint later with **no behaviour change** — which is the fourth
open question in the handoff, answered by construction.

### 2.5 The live worked-seconds basis

`load_live_worked_seconds` (`services/queries/item_economics/live_worked_seconds.py`)
supplies each step's settled working seconds plus the concurrency-averaged share of any
open WORKING interval, loaded once per request and persisted nowhere. Both batched and
single-task surfaces already share it. This endpoint uses the same loader, unchanged —
it is what makes `actual_worked_seconds` a live figure.

### 2.6 The evaluation carries its own rate and currency

`item_cost_evaluations` (`models/tables/item_economics/item_cost_evaluation.py`) holds
`cost_per_worker_minute_minor_snapshot` `Numeric(12,4)` (`:37`),
`production_budget_minor` (`:38`), `allowed_worker_minutes` `Numeric(12,2)` (`:39`) and
`currency` (`:30`, `ItemCurrencyEnum` = `swedish_krona | danish_krona | euro`, matching
the handoff's enum exactly). **The wire enum this surface serves is not this enum** — it
carries a fourth, wire-only member for the no-budget case (§5.1, D3).

**`get_task_price_scenario` uses a different rate.** It builds
`cost_per_worker_minute_ten_thousandths` from `selection.basis_version.
cost_per_worker_minute_minor.scaleb(4)` (`:296-297`) — the **live** basis version,
because a price scenario is a what-if for a price not yet committed. The committed
evaluation carries its own snapshot. They agree until someone effective-dates a new
basis after commit. §4.1 resolves which one this endpoint publishes.

### 2.7 Twelve economics statuses collapse to four verdict states

`EconomicsStatusEnum` (`domain/item_economics/enums.py:15-27`) has twelve members.
`get_task_budget_allocations` treats `{OK, INFEASIBLE}` as budget-bearing
(`_BUDGET_STATUSES`, `:48`) and everything else as no-budget. The handoff asks for no
`status` enum on this surface, on the ground that its twelve values collapse to
`no_budget`. **They do not collapse cleanly: `INFEASIBLE` is budget-bearing** — an
evaluation with `allowed_worker_minutes <= 0`. See card 2 (§10).

### 2.4A The convergence promise, qualified by D9 (round 8)

§2.4 concluded that `production-time`'s `buildOutlook` could converge onto this endpoint
later **with no behaviour change**. **D9 and D10 qualify that**, and the qualification is
recorded here rather than left for the deferred work to discover.

`buildOutlook` gates its projection on the **sum** form — *"if `remaining_commitment <= 0` →
no signal"* — and on an infeasible task the shipped allocator makes that sum identically `0`
(§3.4 cause 2; §12A P12). **So `production-time` shows no amber on any infeasible task
today.** This endpoint, under D9, shows amber on an untouched infeasible task that still has
work ahead. That is new behaviour the owner chose, not a defect of either surface.

Consequence for §8's deferred convergence item: converging `production-time` onto this rule
**would change what that screen renders for infeasible tasks**, and is therefore no longer
the free swap §2.4 described. Everything §2.4 says about feasible tasks — including the
`remainingSeconds: -600` test that motivated populating both pairs — is unaffected.

---

## 3. Mechanism contract — the projection rule

This is the rule the frontend is handing over. It is stated here as contract because a
paraphrase of it is what would drift.

### 3.1 Input: the shipped allocator's section rows

The rule consumes `divide_production_budget(...)["sections"]` for the task, unchanged.
It does not re-group steps, does not recompute allowances, and does not read
`division["steps"]`. **Registers against M1, M6.**

### 3.2 The "still to come" predicate

A section contributes to the remaining commitment when **both** hold:

1. `left_seconds is not None` — which excludes `share_state == "excluded"` sections and
   the whole no-budget case; and
2. its `state` is **not** in `TERMINAL_STEP_STATES`
   (`domain/task_steps/constants.py:4`) — the imported constant, never a locally
   spelled set.

The predicate is written as `not _step_state_is_terminal(...)` semantics over the
section's governing state (§2.3). **Registers against M1.**

### 3.3 The clamp and the floor

```
remaining_commitment = Σ over contributing sections of max(0, left_seconds)
```

The **per-section `max(0, …)` clamp is load-bearing** and survives into the backend
verbatim. The frontend's own reason, quoted because it is the contract: *"A section
already past its own slice contributes nothing rather than a negative: how far it will
keep overrunning is not knowable, and letting it subtract would quietly cancel out
another stage's real remaining work."* **Registers against M3.**

```
projected_over_seconds = max(0, remaining_commitment − remaining_pot_seconds)
```

signalled as `projected_over` only when `projected_over_seconds >= 60`
**and the contributing set is non-empty** — that is, at least one section still has work
to come (**D10, §10.5**). The 60-second
floor exists because the frontend's `formatWorkSeconds` floors to minutes and a smaller
gap announces itself as "0m over". **The floor gates the state, not the figure** — the
raw seconds are always served, so a future notification channel can set its own,
higher bar without a contract change. This answers the handoff's third open question.

**The D10 guard is "is there work still to come", NOT "is the remaining commitment
positive" — and the difference is the whole decision** (owner, 2026-08-24; §10.5).

```
has_work_ahead = any(contributes(section) for section in sections)     # the CONTRIBUTING SET is non-empty
                 # NOT: remaining_commitment > 0
```

**Why the obvious form is wrong, measured (§12A, P12).** For **any** task with
`allowed_worker_minutes <= 0`, `remaining_commitment` is **always exactly `0`** — not
because there is no work left, but because §3.4's cause 2 floors `distributable_seconds`
at zero, so every section allowance is `0` and every `left_seconds` is `≤ 0`, which the
per-section clamp then takes to `0`. A `remaining_commitment > 0` conjunct therefore
suppresses the forecast on **every** infeasible task, including the untouched one with
real work ahead — which is exactly the verdict D9 exists to produce. The contributing-set
form distinguishes the two cases the owner distinguished: *pending work exists* versus
*every section is finished, skipped or absent*.

**This is a deliberate divergence from the shipped `buildOutlook`, not a restoration of
it.** The frontend's rule is the sum form — *"if `remaining_commitment <= 0` → no
signal"* (frontend handoff, "Why the projection cannot be built from that payload") — so
`production-time` shows **no amber on any infeasible task today**. D9 is new behaviour by
the owner's decision, and §2.4's "converge later with no behaviour change" is qualified
accordingly (§2.4A). Like the floor, the guard gates the **state** and not the figure: the
raw seconds are served regardless. **Registers against M1, M3.**

### 3.4 The two-operand accounting divergence (**RESOLVED — D1, owner, 2026-08-24**)

`remaining_pot_seconds` and `remaining_commitment` are drawn from two subtly different
accountings, and **they do not always agree**. Measured this session against the pure
allocator (probe reproduced in §12):

| Fixture | `allowed − actual` | `Σ participating left_seconds` | delta |
|---|---|---|---|
| No excluded steps | 2100 | 2100 | **0** |
| A wholly excluded (skipped) section | 1800 | 1800 | **0** |
| A skipped step **inside an otherwise participating section** | 1800 | 1500 | **−300** |
| An **infeasible** task: `allowed = −12.50` min, one working step at 300 s | −1050 | −300 | **+750** |

**There are two independent causes, and the second was found only after D1 was
answered** (round 2 — recorded because a bound stated on one cause alone was wrong):

1. **Excluded steps are charged twice.** `group_steps_by_section` sums `worked_seconds`
   over **every** non-deleted step in a section including excluded ones
   (`budget_division.py:131`), while `charged_seconds` **also** subtracts every excluded
   step's worked seconds from the distributable pot (`:327`). A skipped step sitting in
   a section that still has live work is charged once against the pot and once against
   its own section's `left_seconds`. Delta contribution: exactly that step's worked
   seconds, negative.
2. **The distributable pot is floored at zero and the task pot is not.**
   `distributable_seconds = max(0, budget_seconds − charged_seconds)`
   (`budget_division.py:328`) while `allowed_seconds` is served unclamped (§6, D2). For
   an infeasible or fully-charged task the sections divide a floor of zero while the
   task pot stays negative. Delta contribution: `charged_seconds − budget_seconds`
   whenever that is positive — **unbounded by the excluded steps' time**, as the fourth
   row shows (+750 from a −750 pot).

Together: `Σ participating left − (allowed − actual)` is
`max(0, charged − budget) − Σ(worked seconds of excluded steps in participating
sections)`. Either term can dominate; they can also cancel.

**Why it matters here and nowhere else so far.** No shipped surface subtracts these two
figures from each other; this rule is the first to do so. The consequence is that
`projected_over_seconds` can be non-zero purely from the double-charge, with no
clamping and no terminal sections in play — which can manufacture a `projected_over`
verdict out of an arithmetic artefact.

**D1 — the owner settled this 2026-08-24: cost the pot side.** The projection's second
operand is

```
remaining_pot_seconds = allowed_seconds − actual_worked_seconds
```

— the **task-level** figures of §5.2, *not* `Σ participating left_seconds`. The badge
and the "Over budget by…" headline beside it therefore derive from one accounting and
can never disagree on the same card. The section rows keep their current, unchanged
values: `divide_production_budget` is not touched (HC-2), and the shipped
`budget-allocations` and `production-time` consumers are unaffected.

**What D1 does *not* do, stated so no criterion overclaims.** It removes the divergence
from *this* surface by choosing one side of it. The double-charge itself is still
present in `budget_division.py` and still visible to anyone who sums section
`left_seconds` — including the frontend's `buildOutlook`, which sums exactly that.
Consequence: until `production-time` converges onto this endpoint (§8, deferred), the
single-task outlook line and this badge can differ by the worked seconds of excluded
steps inside participating sections. **That difference is expected, is bounded by that
quantity, and is not a defect of either surface.** Mechanism-inventory owns turning
this into a contract-grade statement; a phase criterion that asserts the two surfaces
agree exactly would be asserting something D1 does not promise.

**D9 does not touch D1** (owner, 2026-08-24). The projection's second operand is still
`allowed_seconds − actual_worked_seconds`, the task-level figures, **unclamped** — D9
changed only how the *incurred* figure (`over_seconds`, §5.1) and the *served*
`allowed_seconds` (§5.2) treat a negative pot. The single most consequential choice this
document made is unchanged and needed no re-litigation.

**Still a rule-6 mechanism.** D1 answers *which operand*, not *how it is proven*. The
required test shape is a fixture carrying an excluded step inside a participating
section, asserting the verdict follows the pot side — a fixture without that step
cannot distinguish D1 from its alternative and is a row that cannot fail.

---

## 3A. The projection rule at contract grade (mechanism-inventory, round 6)

Deepens §3. Nothing here changes a meaning §3 already carried; it fixes types,
canonical forms, boundaries and the invariant each part must be proven by. Every fact
below was read or measured on the tree at `f376928`, whose `app/` tree is byte-identical
to `4a7cc69` (`git log 4a7cc69..HEAD -- app/` is empty), so §12's shaping probes remain
valid evidence and were **not** re-run.

### 3A.1 The allocator **call** — §3.1's "unchanged" is a claim about the inputs

`divide_production_budget` (`budget_division.py:289-297`) is a pure function of **four**
arguments. §3.1 requires the section rows to be the shipped ones; that is a statement
about the *call*, not only about the callee. The new service builds all four exactly as
`get_task_budget_allocations` does:

| Argument | Value the new service must pass | Why it is load-bearing |
|---|---|---|
| `allowed_worker_minutes` | `evaluation.allowed_worker_minutes` — a `Decimal` off `Numeric(12,2)` — when the task is budget-bearing (§6A.1); otherwise `None` | `None` selects the allocator's no-budget branch: `budget_seconds/charged_seconds/distributable_seconds` are all `None` and every section row gets `left_seconds = None`, `share_state = "no_budget"` (§12A P4) |
| `steps` | one `DivisionStep` per **non-deleted** `TaskStep` of the task, `total_working_seconds` taken **strictly** by `live_seconds[step.client_id]` (`get_task_budget_allocations.py:241`), the list pre-sorted by `(sequence_order is None, sequence_order, client_id)` | a `.get(..., 0)` fallback would silently substitute settled seconds for live ones; the strict index is deliberate and fails loud |
| `typicals_by_section` | `reconcile_task_typicals(...).selected` — the reconciled, item-narrowed typicals (`get_task_budget_allocations.py:284-291`) | **the highest silent-failure risk in this section.** Passing `None` does not raise: `apply_business_fallback` (`typical_filters.py:329-336`) hands every section the weight `Fraction(1,1)`, so the allocator returns an **equal split**. Every `allowance_seconds` and `left_seconds` changes, the projection changes, and this badge disagrees with the step cards the workers app renders off the same allocator — with nothing red anywhere |
| `section_attributes` | `None`, exactly as the batched sibling passes | it feeds only `section_name` and `order_list`, which this rule never reads; supplying them would change section **ordering** and nothing else |

**Invariant on the production path.** For one task and one stored state, the `sections`
list this service divides is element-for-element equal — on `working_section_id`,
`state`, `allowance_seconds`, `left_seconds`, `share_state` — to the list
`get_task_budget_allocations` computes for the same state.
**Named mutation** (`get_task_budget_signals.py`, the **call site**, not the allocator):
replace the `typicals_by_section` argument with `None`. The fixture must carry **at least
two sections with unequal typical times**; one where every section carries the same
typical, or none, cannot observe this and is a row that cannot fail.
**Registers against M1, M6.**

### 3A.2 The "still to come" predicate — its types, and the membership test that fails silently

§3.2's two conditions are evaluated against a **section row**, which is a `dict`, not an
ORM object. Two of its keys carry types an implementer will guess wrong:

| Key | Production type | Values it can hold |
|---|---|---|
| `left_seconds` | `int` or `None` | `None` for `share_state == "excluded"` and for the whole `no_budget` branch; otherwise `allowance_seconds - worked_seconds`, which may be negative |
| `state` | **`str`** — never a `TaskStepStateEnum` | one of the eight `TaskStepStateEnum` **values** (§3A.3); set by `group_steps_by_section` through `_state_value` (`budget_division.py:149`), which returns `getattr(value, "value", value)` |

**The hazard, measured (§12A, P1).** `TERMINAL_STEP_STATES`
(`domain/task_steps/constants.py:4-9`) is a `frozenset` of **enum members**. The section's
`state` is a **string**. Therefore:

```
"completed" in TERMINAL_STEP_STATES            -> False      # always, for every state
"completed" in {s.value for s in TERMINAL_STEP_STATES}  -> True
```

HC-6.2 forbids a locally spelled set. It does **not** by itself prevent the failing form:
importing the constant and testing membership directly is the natural reading of HC-6.2,
compiles, type-checks, raises nothing, and makes the predicate **constantly true** — every
section, including every completed one, is counted as still to come. `projected_over_seconds`
is then inflated by the whole finished commitment of the task and amber badges appear on
tasks that are finishing on time. Nothing crashes; no other test in the repository reddens.

**Contract.** The predicate is exactly:

```
contributes(section) ==  section["left_seconds"] is not None
                     and section["state"] not in _TERMINAL_STATE_VALUES
```

where `_TERMINAL_STATE_VALUES` is a module-level `frozenset[str]` **derived from the
imported constant**, `frozenset(state.value for state in TERMINAL_STEP_STATES)` — derived,
never typed out (charter manifest property 3). Reusing
`budget_division._step_state_is_terminal` is an equally admissible spelling and accepts a
section row unchanged, because `_value` reads `Mapping`s as well as objects (verified,
§12A P1); the batched service already imports a private symbol from that module
(`_loaded_latest_state_record`, `get_task_budget_allocations.py:15`), so the precedent
exists. **The forbidden spellings are two, not one:** a hand-written string set (HC-6.2),
and membership in the enum `frozenset` itself.

**Invariant on the production path.** With one `completed` section carrying positive
`left_seconds` and one `working` section carrying positive `left_seconds`, only the second
enters `remaining_commitment`.
**Named mutation** (`budget_signal.py`, the **definition** of `_TERMINAL_STATE_VALUES`):
replace it with `TERMINAL_STEP_STATES` itself. The named test must redden. A fixture whose
sections are all non-terminal cannot observe this. **Registers against M1.**

### 3A.3 The complete step-state partition — all eight members, enumerated

`TaskStepStateEnum` has eight members (`domain/task_steps/enums.py:4-12`). Two different
frozensets partition them and they are **not** the same set — `completed` is terminal but
**not** excluded, which is the whole reason a finished section still holds a budget slice:

| Step state | in `TERMINAL_STEP_STATES` | in `EXCLUDED_STEP_STATES` | If it is the section's governing state (§2.3), the section… | Its worked seconds… |
|---|---|---|---|---|
| `pending` | no | no | **contributes** | count in `actual_worked_seconds` |
| `working` | no | no | **contributes** | count |
| `paused` | no | no | **contributes** | count |
| `blocked` | no | no | **contributes** | count |
| `completed` | **yes** | no | does not contribute (terminal), but keeps `left_seconds` as an `int` | count |
| `skipped` | yes | **yes** | does not contribute | count in `actual`, **and** are subtracted from `distributable_seconds` — §3.4 cause 1 |
| `failed` | yes | yes | does not contribute | same as `skipped` |
| `cancelled` | yes | yes | does not contribute | same as `skipped` |

Verified by construction (§12A P5): `blocked`, `paused` and `pending` sections each
returned `left_seconds` as an `int` and `_step_state_is_terminal` `False`.

Two derived facts a criterion may rely on, both from `_governing_step`
(`budget_division.py:180-200`, which prefers a non-terminal step):

1. a section's `state` is terminal **iff every one of its non-deleted steps is terminal**;
2. `share_state == "excluded"` **iff every one of its non-deleted steps is in
   `EXCLUDED_STEP_STATES`** — a section holding one `skipped` step and one `working` step
   is *participating*, and its `worked_seconds` include the skipped step's time. That is
   §3.4 cause 1, and it is why D1's required fixture is what it is.

**Registers against M1, M3.**

### 3A.4 The clamp and the floor — arithmetic types, evaluation order, boundaries

```
remaining_commitment    = sum(max(0, s["left_seconds"]) for s in sections if contributes(s))  # int, >= 0
allowed_seconds_raw     = _budget_seconds(evaluation.allowed_worker_minutes)                  # int, MAY BE NEGATIVE
remaining_pot_seconds   = allowed_seconds_raw - actual_worked_seconds                         # int, sign free  (D1)
projected_over_seconds  = max(0, remaining_commitment - remaining_pot_seconds)                 # int, >= 0
over_seconds            = max(0, actual_worked_seconds - max(0, allowed_seconds_raw))          # int, >= 0  (D9)
served allowed_seconds  = max(0, allowed_seconds_raw)                                          # int, >= 0  (D9)
```

**`allowed_seconds_raw` appears twice with two different clamps, and that is the
contract, not an oversight** (§6, D9). The forecast carries the deficit; the incurred
figure does not; the wire carries the floored value so the client's extrapolation of
`over_seconds` is exact. **Named mutation:** clamp `remaining_pot_seconds` as well — the
untouched-infeasible fixture must lose its `projected_over` verdict and redden.
**Second named mutation:** drop the inner `max(0, …)` from `over_seconds` — the same
fixture must flip to `over` and redden.

**Note for the fixture author:** on an infeasible task every section's `left_seconds` is
`≤ 0`, so `remaining_commitment` is `0` and `projected_over_seconds` reduces to
`|allowed_seconds_raw| + actual_worked_seconds`. A fixture that hand-builds section rows
with positive `left_seconds` under a negative pot is constructing a state the allocator
cannot produce — the mistake this round made and caught (§11 round 8).

- Every operand and every result is a Python **`int`**. No `Decimal`, no `float`, no
  `Fraction` enters this rule; `left_seconds` and `budget_seconds` are already integers by
  construction (`budget_division.py:69`, `:375`).
- **The clamp is per section and is applied before the sum**, never to the sum. Summing
  first and clamping once is the exact defect M3 exists to guard, and it is a one-character
  edit away from the correct form.
- `remaining_commitment` is `0` for an empty contributing set — a task with no steps, or
  with every step excluded, or on the no-budget branch (§12A P2, P3, P4).
- The state gate is **two** conditions, not one: `projected_over_seconds >= 60` (D6) **and
  `has_work_ahead`** — the contributing set is non-empty (D10). The first is compared on an
  `int`; the second is a **set emptiness test, never a sum**, because `remaining_commitment`
  is identically `0` on every infeasible task (§3.3, §12A P12). **Both gate `budget_state`
  only.** **Named mutation:** replace `has_work_ahead` with `remaining_commitment > 0`; the
  untouched-infeasible-with-pending-work fixture must lose `projected_over` and redden. `projected_over_seconds` is served whatever its value, so a
  `within_budget` row carrying `projected_over_seconds` in `1..59` is legal and expected
  (§6A.2 row 6). Adjacent boundary pair for an enumerated criterion: `59 -> within_budget`,
  `60 -> projected_over`.
- **Named mutations, one per sub-check** (charter rule 12): (a) move the `max(0, …)` from
  inside the comprehension to around the sum — the M3 fixture must redden; (b) change `>= 60`
  to `> 60` — the `60` row must redden; (c) change `>= 60` to `>= 0` — the `59` row must
  redden. Each must be shown to bite on its own row.

**Registers against M3, M1.**

### 3A.5 Both operands are second-domain integers — never the shipped minute figures

`budget-allocations` publishes `remaining_worker_minutes`, computed in the **minute**
domain: `calculate_remaining_worker_minutes(Decimal(allowed), calculate_actual_worker_minutes(actual_seconds))`
(`get_task_budget_allocations.py:294-295`), where the actual is quantized to two decimals
before the subtraction. It is the field the frontend's shipped red strip reads today, so
reusing it looks exactly like the reuse HC-6 asks for. **It is not.**

Measured (§12A, P10) with `allowed = 60.00` min: `actual = 3599 s` gives
`remaining_worker_minutes = 0.02` (= 1.2 s) where the true remainder is 1 s; `actual = 3601 s`
gives `-0.02` (= −1.2 s) where the true overrun is 1 s. The minute-domain figure carries a
quantization error of up to ±0.005 min = ±0.3 s and is a `Decimal`, not an `int`.

**Contract.** `over_seconds` and `remaining_pot_seconds` are computed **in seconds, from
integers**: `allowed_seconds` is `_budget_seconds(evaluation.allowed_worker_minutes)`
(§5.2 — the same integer the allocator uses as `budget_seconds`, not a second rounding),
and `actual_worked_seconds` is the integer sum of the live map. Deriving either from
`remaining_worker_minutes`, from `calculate_actual_worker_minutes`, or from any minute-domain
value is a defect even though the result usually agrees.
**Named mutation:** replace `over_seconds` with `int(-remaining_worker_minutes * 60)`; the
`actual = allowed + 1 s` row must redden. **Registers against M1, M2.**

**Overclaim guard.** This surface's `over_seconds` and the sibling's
`remaining_worker_minutes` may therefore disagree by up to 0.3 s at the boundary. That is
expected and is not a defect of either surface — the same shape as §3.4's D1 note. No
criterion may assert exact agreement between them.

### 3A.6 The allocator is total on every path this rule takes

Checked so no phase ships a defensive branch for a case that cannot arise, and so no phase
omits one that can (§12A, P2–P4):

| Input | `divide_production_budget` returns | `remaining_commitment` |
|---|---|---|
| no steps at all, budget present | `sections == []`, `distributable_seconds == budget_seconds` | `0` |
| every step excluded | one `"excluded"` row per section, `left_seconds is None`; the whole `distributable_seconds` is allocated to nobody | `0` |
| `allowed_worker_minutes is None` | the no-budget branch; `left_seconds is None` on every row | `0` (and unreachable — §5A.2 short-circuits first) |
| `distributable_seconds == 0` with participating sections | every `allowance_seconds == 0`, `left_seconds == -worked_seconds` | `0` after the per-section clamp |

There is **no** zero-division path: `apply_business_fallback` returns a strictly positive
`Fraction` for every section (the median of the usable typicals, else `terminal=Fraction(1,1)`),
so `total_weight > 0` whenever the allocated set is non-empty, and the weight loop is not
entered when it is empty. **Registers against M1.**

---

## 4. Mechanism contract — the money rule

### 4.1 Which rate (RESOLVED in shaping — §11 S5)

`over_cost_minor` and `projected_over_cost_minor` are computed from the **committed
evaluation's `cost_per_worker_minute_minor_snapshot`**, never from the live basis
version that `price-scenario` uses (§2.6).

Reason: the pot being overrun was derived from that snapshot. Costing its overrun at
any other rate makes the money disagree with the budget it is an overrun *of*, and the
disagreement would appear only after someone effective-dates a new basis — i.e. in
production, months later, silently. This also answers the handoff's fifth open
question: **the rate is per-task, resolved at commit, so two tasks in one list can
carry different rates and the field is correctly per-row.**

`cost_per_worker_minute_ten_thousandths` is served as
`int(snapshot.scaleb(4))` — the same integer scaling `price-scenario` publishes, from
the task's own snapshot. It is **for the frontend's between-poll extrapolation only**
(HC-5); the frontend does not, and per its own money module may not, use it to compute
a displayed figure. **Registers against M2.**

### 4.2 Money is a function call, not a formula (measured)

**The naive implementation is wrong twice, and this section exists because both wrong
answers look right.**

*Wrong answer one — invert the price-scenario chain literally.* `price_scenario.py`
converts price → minor → centiminutes → seconds in two integer steps
(`allowed_centimin` `:116`, `allowance_seconds` `:123`). Inverting that literally
double-rounds through whole centiminutes. Probed over 20,005 cases (5 realistic rates
× 0–4000 seconds): **502 disagreements** with the shipped figure. At one second the
error is 20%. The two-step conversion exists so client and server *thresholds* agree in
the forward direction; **it is not a costing function.**

*Wrong answer two — write the exact single-step rational.*
`round_half_even(seconds × rate_ten_thousandths, 600_000)` is algebraically the correct
composition and is exactly half-even on the true rational. It still disagrees with the
shipped figure on **24 of the same 20,005 cases** — and every one of the 24 is an exact
half-tie. The cause: `calculate_consumed_cost_minor` computes
`Decimal(seconds)/Decimal(60) * rate` at `prec=50` before quantizing, and 1/60 is not
representable, so at an exact tie the 50-digit intermediate has already fallen off the
tie and half-even resolves from the perturbed value — in *both* directions (at rate
3.7500: 136s gives 9 where exact gives 8; 152s gives 9 where exact gives 10).

**Contract: the new surface calls `calculate_consumed_cost_minor`
(`calculator.py:326`) with the overrun seconds and the evaluation's rate snapshot.**
Criterion M2 is then satisfied *by identity* rather than by proof, and the badge, the
valuation editor and any future notification cannot name different money for one task
because there is only one implementation. A reimplementation — however cleaner — is a
defect. **Registers against M2.**

### 4.3 What is costed

- `over_cost_minor` = cost of `over_seconds`.
- `projected_over_cost_minor` = cost of `projected_over_seconds`.

Both through §4.2, both `0` when their seconds are `0`.

---

## 4A. The money rule at contract grade (mechanism-inventory, round 6)

Deepens §4. §4.2 settled *which implementation*; this settles *how it is called*, which is
where the remaining silent failures live.

### 4A.1 The call identity, and the exact types `calculate_consumed_cost_minor` accepts

Signature (`calculator.py:326-341`):
`calculate_consumed_cost_minor(actual_worker_seconds: int, cost_per_worker_minute_minor_snapshot: Decimal) -> int`.
Both parameters pass through `_guard_type` (`calculator.py:83-95`), and the guards are
stricter than the annotations suggest — measured (§12A, P7):

| Argument | Accepted | Rejected, with `TypeError` |
|---|---|---|
| seconds | **`type(value) is int`** — exact, so `bool` is rejected | `True`, `60.0`, `Decimal(60)`, `numpy` integers, anything not exactly `int` |
| rate | `isinstance(value, Decimal)` | `3.75` (float), `4` (int), `None` |

Two consequences the phases must carry:

1. **`over_seconds` and `projected_over_seconds` must be Python `int`s at the call site.**
   `max(0, …)` over `int`s already gives one; a `Decimal` sneaking in from a minute-domain
   derivation (§3A.5 forbids it) raises.
2. **A type slip is not a test failure — it is a production 500.** `run_service`
   (`services/run_service.py:45-65`) catches every non-`DomainError` exception, logs it, and
   returns `DomainError("An unexpected internal error occurred.")` at HTTP **500**. The page
   of 25 tasks fails whole, with no identity the frontend can branch on. This is precisely
   the class rule 6 exists for, and it is why the types are contract and not annotation.

**There is no sign guard.** `calculate_consumed_cost_minor(-60, Decimal("3.7500"))` returns
`-4` (§12A, P7). Nothing in the calculator prevents negative money; the only thing that does
is `over_seconds` and `projected_over_seconds` being `max(0, …)`-clamped before the call
(§5.1, §3A.4). **Invariant on the production path:** for every row served, the value handed
to `calculate_consumed_cost_minor` is `>= 0`. **Named mutation:** remove the outer `max(0, …)`
from `over_seconds`; a fixture with `actual < allowed` must produce a negative
`over_cost_minor` and redden the row that asserts `over_cost_minor >= 0`.

**The prohibited alternate derivations, named so a reviewer can grep for them** (§4.2, and
each was measured to disagree): `round_half_even(seconds * rate_ten_thousandths, 600_000)`
(the exact single-step rational — 24 disagreements in 20 005 cases); any inversion of
`price_scenario.py`'s two-step `allowed_centimin`/`allowance_seconds` chain (502
disagreements); any `minutes * rate` in `float`; and any re-implementation inside
`budget_signal.py`. The only admissible spelling is a call into `calculator.py:326`.
**Registers against M2.**

#### 4A.1A Precision note — the two-step inverse needs its own witnessing duration

The two-step price-scenario inverse disagrees with the shipped call **in aggregate** (502
of the 20,005 probed cases), but not at every exact-rational half-tie used to witness the
other prohibited derivation: at rate `3.7500`, it agrees at 136 and 152 seconds. Its first
disagreement at that rate is 40 seconds (`calculate_consumed_cost_minor` returns `2`; the
two-step inverse returns `3`). A mutation test of that alternative must use 40 seconds or
another independently re-derived disagreement; it may not reuse the 136/152 rows. This
clarifies the evidence requirement only, not the money contract. **Registers against M2.**

### 4A.2 The rate: scaling exactness, and why a committed rate is never zero

`cost_per_worker_minute_minor_snapshot` is `Numeric(12,4)`, `nullable=False`
(`item_cost_evaluation.py:37`), so SQLAlchemy hands the service a `Decimal` at scale 4.
`int(snapshot.scaleb(4))` is therefore **exact and never truncates** — `scaleb(4)` shifts the
exponent to `0` and the coefficient is already integral (§12A, P8: `3.7500 -> 37500`,
`0.0001 -> 1`, `99999999.9999 -> 999999999999`). This is the same integer scaling
`price-scenario` publishes (`get_task_price_scenario.py:296-297`), from **this task's own
snapshot** rather than the live basis version (§4.1). `int()` truncates toward zero, so this
exactness is a property of the column scale, not of the expression: a scale change would
silently start rounding down. **Invariant:** `int(rate.scaleb(4)) * 1 == rate * 10_000`
exactly, asserted on a value read back through the ORM (charter rule 3), not on a hand-built
`Decimal`.

**A committed evaluation cannot carry a zero rate.** `calculate_allowed_worker_minutes`
raises `ITEM_COST_RATE_UNDERFLOW` on a zero rate (`calculator.py:307-310`) and the commit
path computes `allowed` through it (`commit_item_cost_evaluation.py:317-318`), so every
budget-bearing row has `cost_per_worker_minute_ten_thousandths > 0`. Under `no_budget` the
field is `0` by §5A.2, not by arithmetic. **Registers against M2.**

### 4A.3 A non-zero overrun may legitimately cost `0` — the overclaim guard

`calculate_consumed_cost_minor` quantizes to whole minor units with `HALF_EVEN`, so a short
overrun costs nothing at all. Measured (§12A, P11), at four realistic rates:

| Rate (minor / worker-minute) | `over_cost_minor` is `0` for | first non-zero |
|---|---|---|
| `3.7500` | `over_seconds` 1..8 | 9 s -> 1 |
| `12.3456` | 1..2 | 3 s -> 1 |
| `0.9999` | 1..30 | 31 s -> 1 |
| `41.6667` | — | 1 s -> 1 |

D8 gives `over` no floor: one second past the pot is `over`. At a typical rate the first
**eight** seconds of overrun therefore serve `budget_state: "over"`, `over_seconds` in
`1..8`, and `over_cost_minor: 0` — a red badge naming no money. That is correct and must not
be "fixed".

**Two things follow.** (a) The frontend's acceptance criterion 2 —
*"returns `over`, with `over_seconds > 0` **and `over_cost_minor > 0`**"* — is **not
satisfiable in general** and must be corrected in the `to_frontend` handoff (§8, must-ship
item 5). (b) No phase criterion may assert `over ⇒ over_cost_minor > 0`; the assertable
invariant is `over_seconds > 0` and `over_cost_minor >= 0`, plus one enumerated row pinning
the exact figure at a named rate and duration. **Registers against M2.**

**M2 itself is narrower than it reads, stated so no criterion overclaims.** M2 says the two
surfaces agree *for the same duration*, because they are the same call. It does **not** say
this row's `over_cost_minor` equals `budget-status`'s `consumed_cost_minor` for the same
task — `budget-status` costs the **whole** worked time (`get_task_budget_status.py:199`),
this row costs the **overrun**. A criterion comparing the two payload numbers directly is
asserting something M2 does not promise; the assertable form feeds the same `int` to the
same function from both sides.

---

## 5. Domain model — the row, and who owns every field

One flat row per visible task. **No nested array at any depth** (M4).

### 5.1 Authoritative — rendered as served, quotable verbatim by a future notification

| Field | Type | Default | Owner / derivation |
|---|---|---|---|
| `task_id` | string | — | fact: `tasks.client_id` |
| `budget_state` | enum | `no_budget` | **derived**, §6 — the headline verdict |
| `over_seconds` | int ≥ 0 | `0` | derived (**D9**): `max(0, actual_worked_seconds − max(0, allowed_seconds))` — an **incurred** overrun counts only worked time beyond a *real* pot, so a negative pot alone never makes a task `over` |
| `over_cost_minor` | int ≥ 0 | `0` | derived: §4.2 over `over_seconds` |
| `projected_over_seconds` | int ≥ 0 | `0` | derived: §3.3 |
| `projected_over_cost_minor` | int ≥ 0 | `0` | derived: §4.2 over `projected_over_seconds` |
| `currency` | enum | `no_currency` | fact: `item_cost_evaluations.currency`, else `no_currency` (**D3**) |

**D3 — `currency` is a four-member enum (owner, 2026-08-24):**
`swedish_krona | danish_krona | euro | no_currency`.

The first three are `ItemCurrencyEnum` (`domain/items/enums.py:11-14`), which is exactly
the set the frontend asked for. **`no_currency` is a fourth member this surface adds,
and it exists only on the wire** — it is not added to `ItemCurrencyEnum`, which is a
persisted database enum (`item_valuation_currency_enum`) and must not grow a member
that no row can ever hold.

Rule, in full — there is no fallback chain:

- `budget_state != no_budget` ⇒ the task has a current committed evaluation ⇒ serve
  `evaluation.currency`. **Guaranteed present**, because `over` and `projected_over`
  are the only states with non-zero money and both require that evaluation.
- `budget_state == no_budget` ⇒ serve `no_currency`, always — including when the item
  *does* carry a valuation with a currency of its own.

**Why the valuation is deliberately not consulted**, recorded so a later reader does not
"fix" it: reading it costs nothing (the service already loads every requested item's
valuation) but it buys a label for four zeroes at the price of a precedence rule to
specify, test and keep true — and it would be *wrong* in the `CURRENCY_MISMATCH` case,
where the valuation, basis and model currencies disagree and picking the valuation's
silently names one of three conflicting answers as the truth. One rule beats two.

**Consequence the frontend accepted in advance:** their exhaustive switch over
`ValuationCurrency` will not typecheck until they add a `no_currency` arm. That is the
property they asked the enum for, and it can only ever appear beside four zeroes.

### 5.2 Supporting — so the client can tick the figure between polls without re-deriving the verdict

| Field | Type | Default | Owner / derivation |
|---|---|---|---|
| `allowed_seconds` | int ≥ 0 | `0` under `no_budget` | derived (**D9**): `max(0, _budget_seconds(allowed_worker_minutes))` — **the same integer the allocator uses as `budget_seconds`** (`budget_division.py:69`), never a second rounding of the minute figure, then floored at zero so the client's forward extrapolation of `over_seconds` agrees with the server exactly. The **unclamped** figure is still used internally, as the projection's second operand (§3.4, D1) |
| `actual_worked_seconds` | int | `0` | derived: live basis, §2.5 — same as `budget-allocations` |
| `cost_per_worker_minute_ten_thousandths` | int | `0` under `no_budget` | fact-derived: §4.1, extrapolation only |

**The split is the contract** (HC-5): the client renders the served verdict and may
extrapolate only the time-dependent figures forward; it never recomputes the verdict.

### 5.3 Both pairs are populated (owner decision, §11 S2)

`over_*` and `projected_over_*` are **not** mutually exclusive. Every figure that is
non-zero is served; `budget_state` names only the **headline**, with `over` winning
when both apply. This answers the handoff's first open question in the direction the
frontend offered, and §2.4 shows it matches the shipped `buildOutlook` semantics
exactly — so `production-time` can converge onto this rule later with no behaviour
change.

### 5.4 Facts vs derived — the provenance boundary

Nothing in this row is a fact about the world except `task_id`, and `currency` **when
it is not `no_currency`** — under D3 the sentinel is a derived statement that no fact is
available, which is precisely the distinction this section exists to keep. Every
figure is a **derived interpretation of a live basis**, valid at the instant of the
read, and **none of it is persisted** (HC-1). Missing data is never inferred: a task
without a usable committed evaluation is `no_budget` with explicit zeroes, not a task
with a guessed budget.

---

## 5A. The row at contract grade (mechanism-inventory, round 6)

Deepens §5. Ten fields, one flat object, no nesting at any depth (M4).

### 5A.1 Production types and their JSON forms, per field

The sibling serializer renders `Decimal` values as **strings** (`_decimal`,
`division_serializers.py:22-23`), because `budget-allocations` carries minute figures. **No
field of this row is a `Decimal`, and no field is serialized as a string-encoded number.**
Copying `_decimal` into this serializer is a contract break the frontend would see as a type
change.

| Field | Python type leaving the service | JSON form | Notes |
|---|---|---|---|
| `task_id` | `str` (`tasks.client_id`) | string | |
| `budget_state` | `str` | string | one of exactly four literals (§6) — the wire carries the value, not an enum object |
| `over_seconds` | `int >= 0` | number | |
| `over_cost_minor` | `int >= 0` | number | minor units; may be `0` while `over_seconds > 0` (§4A.3) |
| `projected_over_seconds` | `int >= 0` | number | served whatever its value, floor or no floor (§3A.4) |
| `projected_over_cost_minor` | `int >= 0` | number | |
| `currency` | `str` | string | one of exactly four literals (§5A.3) |
| `allowed_seconds` | `int >= 0` | number | served floored at zero (**D9**, §5.2); the unclamped figure stays internal, as the projection's operand (§3.4, D1) |
| `actual_worked_seconds` | `int >= 0` | number | |
| `cost_per_worker_minute_ten_thousandths` | `int >= 0` | number | `> 0` on every budget-bearing row (§4A.2) |

Every key is **present on every row** (HC-4). No key is ever `null`, and no key is ever
omitted — the ABSENT-not-null rule of `decision-money-audience-admin-manager-only` is
satisfied here by the route gate, not by field filtering (§7A.5), so there is no path on
which a key is dropped. **Registers against M4.**

### 5A.2 The `no_budget` row is constructed, never computed

When the task is not budget-bearing (§6A.1) the row is **built from constants**, not derived:

```
{task_id, "no_budget", 0, 0, 0, 0, "no_currency", 0, 0, 0}
```

— all eight numeric fields `0`, including `actual_worked_seconds`, which the task may well
have. This resolves an ambiguity §5.2 left open: its table gives `allowed_seconds` and
`cost_per_worker_minute_ten_thousandths` the qualifier "`0` under `no_budget`" but gives
`actual_worked_seconds` a bare default. Both readings render identically — nothing on a
`no_budget` row is drawn, and the supporting fields exist only for extrapolation against a
pot that does not exist — so this is resolved by contract rather than by an owner card, and
listed for ratification (§10.4, "resolved unilaterally"). The sibling agrees in spirit:
`get_task_budget_allocations.py:298-300` sets `actual_worker_seconds` to `None` on the same
branch.

**Why construction rather than arithmetic.** On the no-budget branch the allocator returns
`left_seconds is None` everywhere, so every figure would *happen* to compute to `0` today.
Short-circuiting before the arithmetic means a future change to the allocator's no-budget
branch cannot leak a non-zero figure onto a row whose state says there is no budget.
**Invariant on the production path:** for a task whose primary item has no committed
evaluation but whose steps carry worked time, every numeric field is `0`.
**Named mutation:** delete the short-circuit and let the general path run; the fixture with
logged work on an unevaluated task must redden on `actual_worked_seconds`.
**Registers against M4.**

### 5A.3 `no_currency` — the mechanics that keep it wire-only

`ItemCurrencyEnum` (`domain/items/enums.py:11-14`) is bound to the Postgres type
`item_valuation_currency_enum` with `create_type=False`
(`item_cost_evaluation.py:30`). Adding a member to it is a **migration**, which HC-1
forbids, and would put a value in the type that no row can hold.

**Contract.** The four-member wire vocabulary is declared in the new pure module
(`budget_signal.py`) as a `frozenset[str]` or `str`-valued enum whose first three members are
**derived** from `ItemCurrencyEnum` — `{c.value for c in ItemCurrencyEnum} | {"no_currency"}`,
derived and never typed out — and the sentinel literal `"no_currency"` appears in exactly one
place in the codebase. The serializer emits `evaluation.currency.value` when the row is
budget-bearing and the sentinel otherwise; there is no fallback chain and the item valuation
is never consulted (§5.1).
**Invariant:** `ItemCurrencyEnum` still has exactly three members and none of them is
`no_currency` — an absence claim, and therefore one that must be shown able to observe the
presence: the probe adds a fourth member to a **copy** of the enum in the test and confirms
the guard reddens (charter rule 15). **Registers against M4.**

---

## 6. `budget_state` — the complete order

Four members. The order is total and stated in full, because downstream criteria will
enumerate it (charter: if the product ranks anything, the intention states the complete
order):

| Rank | Member | Condition |
|---|---|---|
| 1 | `no_budget` | the task is **not budget-bearing** — no current committed evaluation, i.e. economics status outside `{OK, INFEASIBLE}` (D2) |
| 2 | `over` | budget-bearing **and** `over_seconds > 0` |
| 3 | `projected_over` | budget-bearing, not `over`, `projected_over_seconds >= 60` (§3.3), **and at least one section still has work to come** (§3.3, D10) |
| 4 | `within_budget` | budget-bearing and neither of the above |

`no_budget` is evaluated first and wins outright: without a pot, neither overrun figure
has meaning. `over` beats `projected_over` because the badge renders one line and an
incurred fact outranks a forecast — while both figures remain populated (§5.3).

**D2 — `INFEASIBLE` is budget-bearing and reports `over` (owner, 2026-08-24).**
"Budget-bearing" is the shipped `_BUDGET_STATUSES` predicate
(`get_task_budget_allocations.py:48`) — `{OK, INFEASIBLE}` — reused, not respelled
(HC-6). An `INFEASIBLE` task carries `allowed_worker_minutes <= 0`, so its
`allowed_seconds` is zero or negative and **its first logged minute makes it `over` by
the full worked time**. That is the intended reading: an infeasible task is unfunded
from the start, and the list is where a manager would act on the pricing problem.
`no_budget` therefore means *"we cannot say"*, never *"we can say and it is bad"*.

Two consequences a criterion must pin, both reachable only through this rank order:

**Both bullets below were rewritten by D9 (§10.4, owner, 2026-08-24).** The
superseded text is preserved in §11 round 7, because it is what the owner ratified in
round 5 and the record of the correction matters more than a clean page. D2 itself is
**unchanged and is now literally true**: with the pot floored at zero for the incurred
figure, an infeasible task's first logged minute does make it `over` by exactly the full
worked time.

- an `INFEASIBLE` task with **zero** worked seconds is **`projected_over`**, not `over`
  and not `within_budget` (**D9**). Nobody has worked, so nothing is *incurred*; but the
  price was set before anyone started and the pot is already in deficit, so an overrun is
  already **forecast**. The forecast carries the deficit at full size: the projection's
  second operand stays the **unclamped** `allowed_seconds − actual_worked_seconds`
  (§3.4, D1 — untouched), so `projected_over_seconds` is the remaining commitment *plus*
  the size of the hole. This is the boundary row; a fixture that only ever gives
  infeasible tasks worked time cannot observe it, and neither can one whose infeasible
  task has no unfinished sections.
- **the incurred figure and the forecast clamp differently, and the asymmetry is the
  contract** (**D9**). `over_seconds` floors the pot at zero — a fact may only count time
  actually worked. `remaining_pot_seconds` does not — a forecast may legitimately carry a
  known structural deficit. `allowed_seconds` is **served** floored at zero (§5.2), which
  is what keeps the client's forward extrapolation of `over_seconds` exact; the client
  never needs the unclamped pot, because it renders the served verdict and never
  recomputes it (HC-5). This supersedes the round-5 instruction to serve `allowed_seconds`
  unclamped while honouring the reason that instruction gave.

**Why an enum rather than nullability**, recorded because it is a contract and not a
style preference: a future notification fires on **transitions of this field**, not on
levels; it gives the frontend an exhaustive switch that breaks the typecheck when a
member is added; and it separates "not over" from "no budget at all" without a second
field.

---

## 6A. The state order at contract grade (mechanism-inventory, round 6)

Deepens §6. §6 states the ranking; a planner needs a **decision procedure with every tie and
overlap decidable** (charter rule 2), and one of §6's own boundary claims does not survive
contact with the code.

### 6A.1 "Budget-bearing" ⟺ a current committed evaluation exists

§6 defines budget-bearing as "economics status outside `{OK, INFEASIBLE}`" via
`_BUDGET_STATUSES` (`get_task_budget_allocations.py:48`). On the production path that
predicate is **equivalent to a much simpler one**, and the equivalence is what makes §5.1's
"guaranteed present" claim true rather than hopeful:

- when a current committed evaluation exists, the sibling assigns
  `INFEASIBLE if Decimal(evaluation.allowed_worker_minutes) <= 0 else OK`
  (`get_task_budget_allocations.py:229`) — **always** a member of `_BUDGET_STATUSES`;
- when none exists, the status is `NOT_EVALUATED` or one of the nine configuration/valuation
  statuses (`:207-227`) — **never** a member.

Therefore `budget_state != "no_budget"` **iff** the task has a current committed evaluation,
and `evaluation.currency` and `cost_per_worker_minute_minor_snapshot` are guaranteed
non-`None` exactly on those rows. "Current committed" is
`kind == COMMITTED AND superseded_at IS NULL AND is_deleted = false`
(`get_task_budget_allocations.py:96-99`), and **at most one such row can exist per task** —
enforced by the unique partial index `uix_item_cost_evaluations_current`
(`item_cost_evaluation.py:56`), so the `{task_id: evaluation}` map cannot silently drop a
duplicate.

**Contract.** The new service resolves budget-bearing by the *same* predicate the sibling
uses — `_BUDGET_STATUSES` reused, not respelled (HC-6, D2) — and must still compute the
status for the no-evaluation branch, because that branch is what makes the equivalence
observable rather than assumed. **Registers against M4.**

#### 6A.1A Structurally held detail — the no-evaluation branch's status computation

The served `no_budget` row is identical for every non-budget-bearing sibling status, so a
test of this new surface cannot observe whether the sibling's detailed no-evaluation status
branch was computed before its result was collapsed. Keep that branch copied from the sibling
and verify it by source inspection; do not create a vacuous behavioral criterion for it.
This is structurally held until the wire exposes a distinction that can observe the branch.
**Registers against M4.**

### 6A.2 The decision procedure — seven rows, every combination covered

`budget_state` is decided by three predicates in this order. The table is exhaustive over
their combinations; there are no ties, because the ranking is a first-match cascade.

| # | budget-bearing? | `over_seconds > 0`? | `projected_over_seconds >= 60` **and** `remaining_commitment > 0`? | `budget_state` | figures served |
|---|---|---|---|---|---|
| 1 | **no** | — | — | `no_budget` | all eight numeric fields `0` (§5A.2) |
| 2 | yes | yes | yes | `over` | **both** pairs non-zero |
| 3 | yes | yes | no, but `projected_over_seconds > 0` | `over` | over pair non-zero; projected pair non-zero **below the floor** |
| 4 | yes | yes | no, `projected_over_seconds == 0` | `over` | over pair only |
| 5 | yes | no | yes | `projected_over` | projected pair only |
| 6 | yes | no | no, but `projected_over_seconds > 0` | `within_budget` | **projected pair non-zero on a `within_budget` row** |
| 7 | yes | no | no, `projected_over_seconds == 0` | `within_budget` | all four overrun figures `0` |

**The infeasible cases land in these rows as follows.** Every figure below is **derived from
`divide_production_budget`**, not supplied (§12A, P12; `allowed_seconds_raw = -750`):

| Fixture | contributing sections | `over_seconds` | `projected_over_seconds` | row | `budget_state` |
|---|---|---|---|---|---|
| untouched, one `pending` step | **1** | `0` | `750` | 5 | **`projected_over`** |
| untouched, `working` + `pending` | **2** | `0` | `750` | 5 | **`projected_over`** |
| 60 s logged, work still ahead | 2 | `60` | `810` | 2 | **`over`** |
| **all steps skipped, never worked** | **0** | `0` | `750`, served not signalled | 7 | **`within_budget`** |
| all skipped, 500 s logged first | 0 | `500` | `1250` | 4 | `over` |
| all completed, task finished | 0 | `400` | `1150` | 4 | `over` |
| no steps created at all | **0** | `0` | `750`, served not signalled | 7 | `within_budget` |

**Read the `contributing sections` column, not the commitment.** On an infeasible task
`remaining_commitment` is `0` in **every** row — the allocator floors the distributable pot
(§3.4 cause 2) — so it cannot separate row 5 from row 7. Only the emptiness of the
contributing set can, which is why D10 is a set test (§3.3). Rows 4 and 7 also show the guard
gating the **state** while the figure is still served.

**Row 6 is the row a plan will forget.** It is the only place where a served figure and the
served state appear to contradict each other, and it is legal by construction: D6's floor
gates the state, never the figure (§3.3, §3A.4). A criterion set that enumerates rows 1, 2,
5 and 7 looks exhaustive and is not.
**Row 3 is the second.** §5.3 says both pairs are populated and `over` merely names the
headline; a fixture that only ever makes `over` and `projected_over` mutually exclusive
cannot observe it.

**Named mutations, one per sub-check:** (a) make the cascade check `projected_over` before
`over` — rows 2 and 3 must redden, **and so must the "60 s logged" infeasible fixture**,
which is the case where the two verdicts genuinely compete; (b) zero the projected pair
whenever the state is `over` — rows 2 and 3 must redden on the figures; (c) zero the
projected pair whenever the floor is not met — row 6 must redden; (d) delete the
`remaining_commitment > 0` conjunct — the fourth infeasible fixture must redden. **Registers against M4.**

#### 6A.2A Precision amendment — reachable rows and the D10 guard

Row 4 in the table above is unreachable: `over_seconds > 0` implies the raw task pot is
already exceeded, so `projected_over_seconds >= over_seconds > 0`. The completed-task
examples mapped to row 4 are therefore row-3 shapes with a non-zero projection, not a
separate zero-projection state. The table's fourth-predicate header is also superseded:
the D10 guard is `has_work_ahead` (a contributing-set emptiness test), **not**
`remaining_commitment > 0`. The corresponding mutation is to replace `has_work_ahead` with
the commitment-sum test; an untouched infeasible task with a pending section must redden.
Plans enumerate the six reachable rows and may assert the derived invariant
`over_seconds > 0 ⇒ projected_over_seconds >= over_seconds`. This is a precision correction,
not a change to the verdict semantics. **Registers against M4.**

### 6A.3 **RESOLVED — D9 (owner, 2026-08-24).** The negative-allowance, zero-work boundary

§6 makes two statements that cannot both be true, and the code says which one breaks:

- §6, first boundary bullet: *"an `INFEASIBLE` task with **zero** worked seconds is
  `within_budget`, not `over` — `over_seconds` is `max(0, actual − allowed)` and **both are
  zero**, so the rank falls through."*
- §6, second boundary bullet: *"`allowed_seconds` may be **negative** for an infeasible task
  … It is served as-is, **not clamped**."*
- D2 (§6, §10.3): *"its first logged minute makes it `over` by **the full worked time**."*

`INFEASIBLE` is `allowed_worker_minutes <= 0`. The first bullet and D2's sentence are true
**only in the `== 0` sub-case**. For `< 0` they are both false, and the gap is not small.
Measured end-to-end on the shipped calculator (§12A, probe P9): an item priced `100.00`
carrying one cost-model term of `150.00` commits at `production_budget_minor = -5000`
(`calculate_production_budget` returns `min(residual, cap)` with **no floor at zero**,
`calculator.py:273`), giving `allowed_worker_minutes = -1250.00` and
`allowed_seconds = -75000`. With **zero** logged work, §5.1 read literally yields
`over_seconds = max(0, 0 − (−75000)) = 75000` and `over_cost_minor = 5000`. With 60 s logged
it yields `75060`, not the `60` D2's sentence names.

This is reachable by construction, not by corrupt data: nothing floors the production budget
at zero, no check constraint forbids a negative `allowed_worker_minutes`, and the commit path
stores whatever the calculator returns.

**D9 — the owner ruled 2026-08-24, and the ruling is neither branch that was offered.**
A negative pot before anyone works is a **forecast**, not a fact: the price was set before
the work began, so the task is *already projected* to go over. It becomes a **fact** the
moment someone starts working it. In the owner's words:

> *"yes the moment the task transitions to working it becomes over budget, but before
> transitioning to working it displays a projection, because the user has placed the price
> and before some one even works the task is already projected to be overbudget, the moment
> someone starts working with it then it is a fact that is over budget."*

**The mechanism this ruling fixes, in four lines:**

1. `over_seconds = max(0, actual_worked_seconds − max(0, allowed_seconds_raw))` — the
   incurred figure floors the pot at zero, so a negative pot alone never makes a task `over`.
2. `remaining_pot_seconds = allowed_seconds_raw − actual_worked_seconds` — **unclamped, D1
   untouched**, so the deficit enters the forecast at full size.
3. `allowed_seconds` is **served** as `max(0, allowed_seconds_raw)` (§5.2), which keeps the
   client's forward extrapolation of `over_seconds` exact; the client never needs the
   unclamped pot (HC-5).
4. §6 rank 3 gains a **`has_work_ahead`** conjunct (**D10**, §10.5): the forecast requires at
   least one section still to come. Without it, a task with nothing left to do but a negative
   pot forecasts an overrun that can no longer happen. The conjunct is a **set emptiness
   test**, never `remaining_commitment > 0` — that form is identically false on every
   infeasible task and would delete D9's own verdict (§3.3, §12A P12).

**"The moment the task transitions to working" is transcribed as `actual_worked_seconds > 0`,
not as "a step is in `WORKING`", and the difference is load-bearing.** A task worked yesterday
and now paused has no `WORKING` step, but its overrun is still an incurred fact; a state-based
reading would drop it back to `projected_over`. Because the live clock starts accruing the
instant a step enters `WORKING` (§2.5), the two readings coincide at the moment the owner
described and diverge only afterwards — which is exactly where the seconds-based reading is
the right one. Recorded because a paraphrase of an owner's sentence becoming a criterion is a
defect family this project's lineage has already paid for.

**Registers against M4.**

### 6A.4 What M5 promises, and what it does not

M5 reads *"two calls a few seconds apart against unchanged state differ only in the
time-dependent figures — never in `budget_state`, never in row membership or ordering, never
in `allowed_seconds`."* "Unchanged state" must be read as **unchanged stored state**, and the
live basis keeps moving while stored state does not: `load_live_worked_seconds` adds the
concurrency-averaged share of any open `WORKING` interval, measured against `ctx.now`
(`live_worked_seconds.py:59-82`). So the served figures move between two calls **by design**,
and `budget_state` can legitimately change with them when a threshold is crossed.

The partition, so a criterion asserts the right half:

| Invariant across two calls on unchanged **stored** state | Free to move |
|---|---|
| `task_id`, row membership, row ordering (§7A.2) | `actual_worked_seconds` |
| `allowed_seconds`, `currency`, `cost_per_worker_minute_ten_thousandths` | `over_seconds`, `over_cost_minor` |
| `budget_state` — **only when no step of the task is in `WORKING` with an open state record** | `projected_over_seconds`, `projected_over_cost_minor` |

**The stability property that actually holds, and is provable.** With `allowed_seconds` fixed
and `actual_worked_seconds` non-decreasing, `over_seconds = max(0, actual − allowed)` is
non-decreasing: **`over` is absorbing** — once a task reads `over`, no later poll returns it
to `within_budget` without a stored-state change. That is the anti-flicker guarantee M5 is
after, and it is the one a test can prove.

`projected_over` carries **no such guarantee**: as work accrues, `remaining_commitment` and
`remaining_pot_seconds` both fall, and their difference is not monotone, so a task can cross
the 60-second floor in both directions. **The floor is the only hysteresis this endpoint
has**, and §7.4 already assigns anything stronger to whatever fires the event. A criterion
asserting `projected_over` stability across polls on a live task would be asserting something
this design does not promise; the assertable form pins the absorbing property of `over` and
the exact `59/60` boundary of the floor. **Registers against M5.**

---

## 7. Operations

### 7.1 Surface

- **Endpoint:** `GET /api/v1/item-economics/tasks/budget-signals`
- **Roles:** ADMIN, MANAGER (HC-3).
- **Request:** repeatable `task_ids`, hard cap **50**, mirroring `budget-allocations`.
- **Response:** standard `build_ok` envelope, single key `budget_signals`.
- **Mounting:** the fixed batch path must precede the parameterized `/tasks/{...}`
  route block, as `budget-allocations` already does
  (`routers/api_v1/item_economics.py:347`).

### 7.2 Naming (proposed — §11 S6)

| Artifact | Path |
|---|---|
| pure rule | `app/beyo_manager/domain/item_economics/budget_signal.py` (**new module**, so `budget_division.py` is not touched at all — HC-2) |
| query service | `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py` |
| serializer | `serialize_budget_signals` in `domain/item_economics/division_serializers.py` |
| route | `route_get_task_budget_signals` |
| over-cap identity | `BUDGET_SIGNALS_TOO_MANY_TASK_IDS` |

### 7.3 Batch semantics

Unknown, deleted and other-workspace ids are **omitted silently, not an error** — as
`budget-allocations` does. Every other requested task is present, including
`no_budget` ones (M4). Over-cap returns the standard error envelope with the stable
identity above (handoff criterion 8). Row ordering is deterministic and independent of
request order or clock. **Registers against M4, M5.**

### 7.4 Polling and events

No socket event in v1. The frontend polls on its existing 45-second interval. When
notification work lands, both sides expect to revisit this and prefer an invalidation
signal over a shorter poll. **Hysteresis, dedup and per-channel thresholds belong with
whatever fires the event** — `services/infra/schedulers/` and
`workers/notification_worker.py` already exist for that — and **not** in this
endpoint, which stays a pure read naming the current verdict. This answers the
handoff's second open question. Nothing in this pipeline builds it (§8).

---

## 7A. Batch, ordering, error and boundary contracts (mechanism-inventory, round 6)

Deepens §7.

### 7A.1 Cardinality, duplicates, and the visibility predicate

- **`task_ids` is a required repeatable query parameter.** The sibling declares
  `task_ids: list[str] = Query(...)` (`routers/api_v1/item_economics.py:352`). Omitting it
  entirely never reaches the service: FastAPI returns its **own** 422 with body
  `{"detail": [...]}` — a **different envelope** from `build_err`'s `{"error", "ok"}`
  (`routers/http/response.py:14-23`). Two different 422 shapes therefore exist on this route
  and the frontend must not assume one. Documented in the `to_frontend` handoff (§8).
- **The cap is checked on the raw list, before dedup and before any query** — `len(task_ids) > 50`,
  mirroring `get_task_budget_allocations.py:53`. Fifty duplicates of one id pass the cap.
  Adjacent enumerated pair: **50 passes, 51 raises**.
- **Duplicate ids collapse.** The visibility query is `Task.client_id.in_(task_ids)`, so `k`
  copies of one id produce **one** row. M4's "N tasks → N flat rows" is therefore exactly
  *"one row per **distinct visible** requested id"*, and a criterion phrased as
  `len(rows) == len(task_ids)` is false for a duplicate-bearing request. Resolved by contract,
  not by an owner card: the sibling has behaved this way since it shipped and no consumer
  sends duplicates.
- **The visibility predicate is exactly three clauses** (`get_task_budget_allocations.py:61-63`):
  `Task.workspace_id == ctx.workspace_id`, `Task.client_id.in_(task_ids)`,
  `Task.is_deleted.is_(False)`. Everything else — unknown, deleted, other-workspace — is
  **omitted with no marker**: no null row, no `warnings` entry, no error (D7).
  `warnings` stays `[]`.
- **Invariant on the production path:** a request mixing one visible id, one deleted id, one
  id from another workspace and one invented id returns exactly one row.
  **Named mutation:** drop the `is_deleted` clause; the deleted-task row must appear and
  redden the count assertion. **Registers against M4.**

### 7A.2 Row ordering — the sibling does not have it, and this surface promises it

`get_task_budget_allocations` iterates `tasks` straight off an **unordered** `select(Task)`
(`:58-67`), so its row order is whatever the database plan returns and is not part of any
contract. §7.3 promises this surface's order **is** deterministic and independent of request
order and clock, so the new service must establish it explicitly.

**Contract.** Rows are sorted by `task_id` ascending, by the string's own ordering, applied in
**exactly one place** — either `.order_by(Task.client_id.asc())` on the visibility query or a
final `sorted(rows, key=lambda row: row["task_id"])` — never both, and never dependent on
`ctx.now` or on the request's order.

**The fixture that can actually observe this.** Two calls in one test, against a small table,
will agree in row order **even with no ordering at all**, because Postgres returns a
sequential scan in physical order. The discriminating fixture requests the same ids in
**reversed** request order and asserts the response order is unchanged, on a fixture whose
task `client_id`s are **not** in insertion order. **Named mutation:** delete the ordering
clause; that test must redden. **Registers against M5.**

### 7A.3 Error identity, and the envelope it arrives in

`BUDGET_SIGNALS_TOO_MANY_TASK_IDS` is raised as
`ValidationError("BUDGET_SIGNALS_TOO_MANY_TASK_IDS: at most 50 task ids may be requested")`.
`ValidationError.http_status` is **422** (`errors/validation.py:4-5`); `run_service` returns a
failed `StatusOutcome` and `_run` calls `build_err`, producing
`{"error": "<the entire message>", "ok": false}` at 422.

**The identity is the prefix of the `error` string up to the first colon.** There is no
separate code field on this envelope — exactly as `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`
behaves today. A criterion pinning the identity asserts the prefix, not the whole sentence
(charter rule 13).

**Everything else is a generic 500.** `run_service` converts any non-`DomainError` exception
into `DomainError("An unexpected internal error occurred.")` at HTTP 500 with no identity.
That is the failure mode a type slip (§4A.1) or a missing `live_seconds` key produces.
**Registers against M4.**

### 7A.4 Route precedence and mounting

FastAPI matches in **declaration order**. There is today no bare `GET /tasks/{param}` route in
`item_economics.py`, so a fixed `/tasks/budget-signals` cannot currently be shadowed — but
the durable guard is placement, not the current absence.

**Contract.** The new decorator is declared **immediately after**
`@router.get("/tasks/budget-allocations")` (`routers/api_v1/item_economics.py:348`), which
puts it ahead of every parameterized `/tasks/...` GET in the file and keeps the two batch
paths adjacent. **Invariant:** a request to `/api/v1/item-economics/tasks/budget-signals`
dispatches to `get_task_budget_signals` and to no other service — the shape
`test_budget_division_routes.py` already uses for the sibling. **Registers against M6.**

### 7A.5 The authorization boundary

`decision-money-audience-admin-manager-only` (architecture graph) requires a withheld
monetary key to be **ABSENT, never null**, and warns against role checks inside serializers.
This endpoint satisfies it **by construction rather than by subtraction**: the whole route is
gated `require_roles([ADMIN, MANAGER])`, there is no worker or seller variant (HC-3, S4), and
therefore no code path on which a monetary key is dropped. This is the same construction
`price-scenario` uses. No `include_monetary` flag exists on this serializer and none must be
added — a flag would be the "fails open as soon as a new call site appears" mechanism that
decision explicitly rejected.

**Invariant:** WORKER and SELLER receive **403** and the service is never entered; ADMIN and
MANAGER receive 200. This is discharged by adding the route to `_ROUTES` (and **not** to
`_ALL_ROLE_ROUTES`) in `app/tests/unit/routers/api_v1/test_item_economics_router.py`, which
is HC-2a artifact 3. **Registers against M6.**

### 7A.6 HC-2a and HC-7, corrected against the tree

Both statements were re-derived this session; neither correction is semantic.

- **HC-2a artifact 1 carries a fourth literal.** The count assertions are at
  `test_phase9_item_economics_route_mirror.py:127-128` as HC-2a says, and the README row
  assertion at `:115`, and `_EXPECTED_ROUTES` opens at `:33` with the sibling's row at `:60`.
  What HC-2a does not name is the **test function's own name**,
  `test_the_registry_ships_twenty_six_routes` (`:124`), which becomes false when the count
  becomes 27. It is inside artifact 1, so **HC-2a's "exactly four artifacts" still holds** —
  but a phase that edits only the two assertions ships a lie in an identifier.
- **The four artifacts are still four.** Checked for further tripwires: `docs/` living-docs
  tests (`test_item_economics_docs.py`) enumerate no routes;
  `test_item_economics_handoff_accuracy.py` guards a hand-written 23-route set belonging to
  the two 2026-08-15 handoffs and matches error identities only against
  `ITEM_COST_*`/`ITEM_MONEY_MOVED`, so neither the new path nor
  `BUDGET_SIGNALS_TOO_MANY_TASK_IDS` trips it; `routers/README.md` is **hand-maintained with
  no generator** (its own header says so). One caveat for the future: that file's
  `test_no_document_invents_a_fully_qualified_item_economics_path` would redden if the new
  path were ever added to `docs/domains/item_economics/api.md` or `README.md` — so it must
  not be, and the `to_frontend` handoff (a new dated document) is not in its parametrize
  list.
- **HC-7's "twelve statements per request" is not a fixed count.** The sibling issues twelve
  statements *plus one averaging sweep per distinct user holding an open `WORKING` state
  record*: `load_live_worked_seconds` runs one probe query and then one
  `compute_record_contributions` per such user (`live_worked_seconds.py:41-70`). HC-7's point
  — that this buys payload and ownership, not query cost, and is not a cheap sweep — is
  unaffected and if anything strengthened. **Registers against M6.**

### 7A.7 Where the serializer lives, and the one pattern deviation this project inherits

Architecture contract `46_serialization.md` states that services never call serializers and
routers pick the view. The shipped item-economics batch surfaces **already deviate**:
`get_task_budget_allocations` returns `serialize_budget_allocations(output)` from inside the
service (`:314`). §7.2 places the new serializer in `division_serializers.py` and the service
calls it, which is consistency with the sibling rather than with the general contract.
Recorded here so the planner carries the deviation **with its reason** and a reviewer does not
file it as a finding: matching the surface being mirrored beats matching the general contract
when HC-2 forbids touching the surface. Not a semantic change; no owner decision.

---

## 8. Scope ladder

**Must ship:**

1. The pure projection rule (§3) with the clamp and the floor.
2. The money rule (§4) as a call into the shipped function.
3. The batched service, serializer and route (§7).
4. The four HC-2a route-mirror artifacts.
5. A `to_frontend` handoff answering all five of the handoff's open questions, issued
   as a **new dated document** — never an edit of the 2026-08-23 file (memory:
   `never-rewrite-a-published-handoff`).

**Only if cheap:** nothing. This is a one-surface pipeline; anything that looks cheap
here is scope.

**Explicitly deferred — non-goals:**

- **Any background scheduler or workspace-wide sweep.** HC-7: this endpoint is not a
  cheap read, and a sweep over all open tasks is a different query-shape problem.
  Owner decision, §11 S1.
- **Any event, notification, or transition detection**, and the persisted
  last-known-state a transition would require. Owner decision, §11 S1.
- **Deleting `buildOutlook` / converging `production-time` onto this rule.** §2.4
  establishes it can be done with no behaviour change; it is a separate, later, and now
  cheap piece of work. Recorded as answered, not scheduled.
- **Any worker/seller variant** (HC-3).
- **Any change to `budget-allocations`** (HC-2) — the workers-app step cards keep it.

---

## 9. Pre-implementation protocol

1. This document reaches **RATIFIED** by the owner's explicit act. Nothing downstream
   compiles against it until then.
2. **mechanism-inventory** runs and must produce contract-grade definitions for at
   minimum: §3.4 (the accounting divergence — rule 6, highest silent-failure risk in
   this pipeline), §4.1/§4.2 (money and rate), §6 (the state order and its
   `INFEASIBLE` edge), and the batch/ordering determinism behind M5.
3. **implementation-planner** sizes phases at **≤ 8 criteria** each. On the current
   shape this is plausibly two phases — the pure rule, then the service/route/wire —
   split at the seam where the contract is stable (charter phase-sizing corollary).
4. Every criterion row carries a trace cell citing an **M-entry or a §3/§4 contract**.
5. Architecture-graph delta recorded at each phase close: this adds one `endpoint` node
   and one `projection` node under `domain-item-economics`, plus `reads_from` edges
   mirroring `projection-item-economics-task-budget-allocations`.

---

## 10. Owner decisions — **ALL ANSWERED (D1–D10); only the re-ratification act remains** — and the ratification surface

**D1–D10 are answered and are not re-litigated.** Nothing remains open except the owner's
re-ratification act itself, on the surface at §10.6. Each decision lives in the section it
governs, per the artifact map; they are indexed here, not restated:

| ID | Decision | Answered | Lives in |
|---|---|---|---|
| **D1** | The projection subtracts the **task** pot (`allowed − actual`), never the section sum | owner, 2026-08-24 | §3.4 |
| **D2** | `INFEASIBLE` is budget-bearing and reports `over`; `no_budget` means "we cannot say" | owner, 2026-08-24 | §6 |
| **D3** | `currency` gains a wire-only fourth member `no_currency`; no fallback chain | owner, 2026-08-24 | §5.1 |
| **D4** | **Ratification** — "Yes — ratify as presented", on the §10.1 surface | **owner (David), 2026-08-24** | §10.2, §11 round 5 |
| **D5** | HC-2 stands; the worker time-pressure handoff is a **separate project** (resolves §11 R4-c) | owner, 2026-08-24 | §10.3, HC-2 |
| **D6** | The amber (`projected_over`) floor is **60 seconds**, as the frontend chose | owner, 2026-08-24 | §10.3, §3.3 |
| **D7** | Unknown / deleted / other-workspace ids are **omitted silently**, as `budget-allocations` does | owner, 2026-08-24 | §10.3, §7.3, M4 |
| **D8** | `over` has **no floor** — one second over the pot is `over` | owner, 2026-08-24 | §10.3, §6 |
| **D9** | A negative pot before any work is a **forecast**, not a fact: zero-worked infeasible is `projected_over`; the first worked second makes it `over`. Incurred figure floors the pot, forecast does not, wire serves it floored | **owner, 2026-08-24** | §10.4, §6A.3, §5.1, §5.2, §6 |
| **D10** | No work left to come ⇒ no forecast. Skipped-out steps add no time, so no overrun and no projection; work still ahead keeps the forecast. Implemented as a **contributing-set emptiness test**, not a commitment sum | **owner, 2026-08-24** | §10.5, §3.3, §6, §6A.2 |

Shaping resolutions the owner did not need to arbitrate (repo-derivable, each with a
rationale in §11): **S4** roles, **S5** rate source, **S6** naming, **S7** money is a
call, **R2-a** the workspace-currency correction, **R2-b/c** the second divergence cause.

---

### 10.1 The ratification surface (presented to the owner 2026-08-24; **answered — see §10.2**)

This is the surface the intention gate requires, written into the document rather than
left in a conversation, because **this shaper's session ends at this draft** (§11 round
3) and whoever next sits with the owner must be able to relay it verbatim without
having been present. Nothing below is new; it is the four things the gate asks for.

**1 — What the system is trying to achieve.**
The managers task list should be able to say, per task, *"this one is over budget by
this much, and that costs this much"* — and *"this one isn't over yet, but it's heading
there"* — without the app working any of it out for itself. Today the list downloads a
full per-step breakdown to render two numbers, and the "heading there" warning can't be
built from that data at all, so the rule for it lives in the frontend. This moves the
rule to the backend, next to the arithmetic it depends on, and sends one flat answer
per task.

**2 — The measurement ledger, verbatim.** All six entries of §1A, reproduced here so
the owner ratifies the text and not a summary of it:

| ID | Observable outcome | Defect family it guards |
|---|---|---|
| **M1** | For a task not yet over budget whose unfinished sections' remaining targets exceed its remaining pot by at least the agreed floor, the endpoint returns `projected_over` with `projected_over_seconds > 0` — computed in the backend, from section rows the client never receives. | **The rule that lives in two places.** A projection re-implemented client-side against a payload that cannot express it, drifting from the server's arithmetic the first time either moves. |
| **M2** | `over_cost_minor` for a given task and duration equals, to the minor unit, the figure `budget-status` names for the same duration on the same task — because both are the **same function call**, not two agreeing derivations. | **Two screens naming different money for one task.** Measured: an independently-derived exact half-even disagrees with the shipped function on 24 of 20,005 probed cases, all at exact half-ties. |
| **M3** | A section already past its own slice contributes **0** to the projection, never a negative — and a fixture where one section's overrun would otherwise cancel another section's real remaining work produces a signal, not silence. | **The quiet cancellation.** Letting an overrunning section subtract erases a different stage's genuine remaining commitment and the task reads as fine. |
| **M4** | Every visible requested task is **present** with an explicit `budget_state`, including `no_budget` ones; only unknown, deleted and other-workspace ids are omitted. N tasks → N flat rows, **no nested array at any depth**. | **Silent omission read as reassurance.** A dropped task renders as no badge, which a manager reads as "within budget". |
| **M5** | Two calls a few seconds apart against unchanged state differ only in the time-dependent figures — never in `budget_state`, row membership or ordering, or `allowed_seconds`. | **Verdict flicker.** `budget_state` is the intended future event trigger; a verdict that oscillates at a boundary becomes a notification per poll. |
| **M6** | No existing payload, rule or persisted value changes: the four sibling endpoints serve byte-identical responses for identical state, and the four enumerated route-mirror artifacts are the only pre-existing files touched. | **Collateral regression.** The workers-app step cards and the managers single-task surface both ride the read models this feature reuses. |

**3 — The scope boundaries that matter.**

*Ships:* one batched read-only endpoint (repeatable task ids, cap 50, admin/manager),
the projection rule and the money rule in the domain, and a new dated handoff back to
the frontend answering all five of its open questions.

*Explicitly does not ship:* any background scheduler or workspace-wide sweep; any
event, notification or transition detection; deleting the frontend's `buildOutlook`;
any worker or seller variant; any change whatsoever to `budget-allocations`, which the
workers app depends on as-is.

**4 — Consequential decisions outstanding.** **None.** D1–D3 are settled and folded.
The only act remaining is D4 — the ratification itself.

---

### 10.2 D4 — the ratification act (**ANSWERED: ratified, 2026-08-24**)

**Question:** do you ratify this intention — the objective, the six measurement
outcomes above, and the scope boundaries — as the authority every plan and test
downstream derives from?

**Story:** this is the pipeline's strongest gate. Once ratified, prompts of every role
compile against this document, and criteria may cite only its measurement entries or
its mechanism contracts. A vague outcome here becomes an untestable criterion three
sessions from now, and the pipeline has no way to recover it downstream.

**Branches:**
- *Ratify*: mechanism-inventory runs next, on §3.4, §4 and §6.
- *Ratify with modifications*: name them; they are folded and the surface is presented
  again.
- *Not yet*: the document returns to COLLABORATING.

**Recommendation:** ratify. Every decision the shaping surfaced is answered, and the
three mechanisms carrying real silent-failure risk (§3.4, §4.2, §6) are written as
contracts with the measurements behind them rather than as adjectives.

**On silence:** the gate holds. Nothing downstream compiles. **Silence never ratifies**,
and neither does this recommendation.

**How to record it:** replace the status header with `RATIFIED`, and append a §11
changelog entry naming the owner, the date, and *this* surface (§10.1) as the one
presented. Only the owner's explicit act writes it.

**Trace:** the whole document; charter intention gate.

**Answer (owner, David, 2026-08-24): "Yes — ratify as presented."** Presented through
the harness's decision prompt after the four §10.3 confirmations, with the §10.1 surface
relayed whole in the same message — the outcome statement, all six ledger entries with
their defect families, the ship / does-not-ship boundary, and the decision index. The
owner had been told, before answering, that from the moment of ratification every plan
and prompt compiles against this document and that a later change of meaning re-opens
the gate rather than slipping in.

---

### 10.3 D5–D8 — confirmations taken on the ratification surface

The owner is ratifying for the first time in this pipeline and asked to be walked
through it. Four places where the document had made a call **on the owner's behalf** —
inherited from the frontend's handoff or from a sibling endpoint — were put to the owner
as one-line questions with a story each, **before** the ratification question. All four
confirmed the text as written; **no section changes**. They are recorded so a future
reader knows these were consciously owned, not passively inherited.

| ID | Confirmed | Story put to the owner | Alternative declined |
|---|---|---|---|
| **D5** | **HC-2 stands. The worker time-pressure handoff (`HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md`) is a separate project** with its own intention and ratification, free to extend `budget-allocations` there. This was the one item that *blocked* ratification (§11 R4-c) and it is now resolved. | A worker mid-step when a deploy lands: if both requests share one project and one changes `budget-allocations`, a mistake there breaks the step card this project swore not to touch. | Merge into one project (re-shape, gate re-opens); or sequence the worker project first. |
| **D6** | **The `projected_over` floor is 60 seconds** (§3.3), as the frontend chose for its minute-rounding formatter. Raw seconds are always served regardless. | Three stages left whose targets sum to 90 s more than the pot: 60-s floor shows amber "1m over"; a 5-minute floor shows nothing. | A higher floor — fewer amber badges, but the single-task outlook and the list disagree until that screen converges. |
| **D7** | **Unknown, deleted and other-workspace ids are omitted silently** (§7.3, M4), matching `budget-allocations`. | A colleague deletes a task; the next 45-second poll drops the row and the badge vanishes. | Error on any unknown id — one stale id fails the page of 25, and the frontend needs a second error path. |
| **D8** | **`over` has no floor** (§6): `over_seconds > 0` is `over`. | The clock ticks past the pot at 14:03:00; at 14:03:01 the strip is red and reads "0m over" for 59 s — a frontend rounding choice, not a backend one. | The same 60-s floor as amber — symmetric, but a task 59 s over reports `within_budget` and a future `over` notification fires a minute late. |

**What D5 does to the header warning.** §11 R4-c said HC-2's survival had to be decided
before phase 1. It is decided: HC-2 survives. A planner may now cite HC-2 and M6 without
a caveat.

---


### 10.4 D9 — the negative-allowance boundary (**ANSWERED: owner, 2026-08-24**)

**Question:** when a task's budget is negative and nobody has worked on it yet, should the
list say it is over budget — or should the negative budget count as zero until someone
actually logs time?

**Story:** an item comes in priced at 100 kronor and the cost model takes 150 kronor of it in
terms. The system commits the task anyway, with a production budget of minus 50 kronor — about
minus 20 hours of worker time. Nobody has touched the task. Tomorrow morning the manager opens
the list and, as the document reads today, sees a red strip on it: *over budget by 20h 50m,
50.00 kr*. Nobody has worked a second. The next week another such item arrives, and another,
and the red strip stops meaning "someone is running long" and starts meaning "the pricing is
odd" — which is a different message the strip cannot carry.

**Branches:**
- **A — keep it literal.** The badge counts the negative budget as overrun from the moment the
  task exists: untouched tasks show red with real money, and the figure grows by every second
  worked on top of it. Two sentences you ratified are then wrong and get deleted.
- **B — floor the pot at zero for the overrun figures.** An untouched infeasible task reads
  *within budget*; its first logged minute makes it over by exactly that minute, which is what
  you were told the rule did. The pot is then also served as zero, so the app's between-poll
  ticking still matches the server.

**Recommendation:** **B** — it is the only branch under which the two sentences you were
actually shown ("zero worked seconds is within budget", "the first logged minute makes it over
by the full worked time") are true, and it keeps the red strip meaning *work that ran long*
rather than *a price that never added up*.

**On silence:** the gate holds. The document stays COLLABORATING, no plan is written, and no
phase is implemented. Nothing is guessed.

**Trace:** §6A.3; §6's two boundary bullets and D2; §5.1 `over_seconds`; §3.4 D1
`remaining_pot_seconds`; M4.

**Answer (owner, David, 2026-08-24) — neither branch as offered; a third the card did not
carry.** Verbatim:

> *"about the owner card, the recommendation holds part of the answer, yes the moment the
> task transitions to working it becomes over budget, but before transitioning to working it
> displays a projection, because the user has placed the price and before some one even works
> the task is already projected to be overbudget, the moment someone starts working with it
> then it is a fact that is over budget."*

The card's branch B was right that an untouched task must not read `over`, and wrong that it
should read `within_budget`: the deficit is **known in advance**, which is precisely what a
projection is for. Folded as §6A.3 and into §5.1, §5.2, §6 and §3A.4. **D1 is untouched.**
The §1A measurement ledger is untouched — all six outcomes read exactly as ratified in
round 5, and M1's wording already covers the new case.

**Resolved unilaterally this round, listed for ratification alongside D9** (no section changes
meaning, each recorded where it lives): §5A.2 — under `no_budget`, `actual_worked_seconds` is
served as `0` rather than as the task's real live figure, resolving an ambiguity §5.2 left
between its own qualifiers; §7A.1 — M4's "N tasks → N rows" is read as one row per **distinct**
visible id, because duplicate ids collapse in the sibling's `IN` clause; §7A.2 — row ordering
is by `task_id` ascending, chosen because §7.3 already promised determinism and the sibling
does not implement it; §7A.7 — the serializer is called from the service, matching the sibling
rather than architecture contract `46_serialization.md`.

---

### 10.5 D10 — no work left to come, no forecast (**ANSWERED: owner, 2026-08-24**)

**Question:** when a task has no work left to do at all, but its budget was negative from the
start, should it keep showing an amber "heading over budget" warning?

**Story:** the 100-kronor item with 150 kronor of costs comes in, and every step on it gets
skipped — the piece was not worth doing and someone closed it out without logging a minute.
Under the rule you just set, the task still carries its 20-hour hole, so the list keeps
showing amber on it: *heading 20h 50m over*. There is no work left to head anywhere. Six
months later it is still amber, and the manager has learned to ignore amber.

**Branches:**
- **A — restore the guard.** No unfinished work means no forecast: the task drops out of amber
  and reads as within budget. This is what the frontend's own shipped rule already does — the
  guard exists in their code and was lost when this document transcribed the rule.
- **B — leave it.** Any task with a negative budget shows amber forever, whether or not
  anything remains to be done, on the grounds that the pricing problem is real regardless.

**Recommendation:** **A** — it is the frontend's existing behaviour, so the single-task screen
and the list agree; and an amber that can never clear is an amber people stop reading. The
raw number is still served either way, so nothing is hidden from a future notification.

**On silence:** the gate holds. The document stays COLLABORATING and nothing is planned.

**Answer (owner, David, 2026-08-24) — branch A, reasoned from the domain rather than from the
card.** Verbatim:

> *"the thing is that if all the task steps where skipped before production ran then there is
> not aditive time that is placed on the budget thus no over budget nor projection happens.
> does that solve the conflict or perhaps im not understanding the problem enterely"*

**It does solve it, and the reasoning is correct at the source.** Verified: when every step of
a task is skipped, every section comes back `share_state == "excluded"` with
`left_seconds is None`, so the contributing set is empty and no time reaches either figure
(§12A P12). Nothing about skipped work is additive.

**But the card's own branch A did not implement that reasoning, and this round had it wrong.**
Branch A was written as `remaining_commitment > 0`. Deriving the commitment from the real
allocator instead of assuming it showed that `remaining_commitment` is **identically `0` on
every infeasible task** — §3.4 cause 2 floors the distributable pot, so no section ever holds a
positive `left_seconds` under a non-positive budget. That conjunct would have suppressed the
forecast on the untouched task with real work ahead, i.e. deleted D9's own verdict one round
after it was made. **The owner's sentence names the right distinction and the card named the
wrong mechanism for it.** Folded as the contributing-set emptiness test (§3.3, §3A.4, §6A.2),
which separates *work still to come* from *every section finished, skipped or absent* exactly
as the owner's sentence does. Recorded in full at §11 round 8.

### 10.6 The re-ratification surface (rounds 7–8) — everything that changed since the owner's round-5 act

The intention gate re-opened, so it must close the same way it opened: on a surface written
into the document, relayable verbatim by someone who was not present (§10.1's own reason).
**This surface is deliberately a diff, not a restatement.** What is not listed here has not
changed since the owner ratified it on 2026-08-24.

**1 — What is unchanged, and therefore not up for re-ratification.**
The objective (§1). **All six measurement outcomes, M1–M6, verbatim as ratified** (§1A) — no
entry's text moved, and M1's existing wording already covers the case D9 created. The scope
boundaries (§8), ships and does-not-ship. **D1** (the projection subtracts the task pot,
unclamped), **D2** (`INFEASIBLE` is budget-bearing), **D3** (`no_currency`), **D5**–**D8**.

**2 — The one meaning that changed: D9.**
A task whose budget was negative before anyone touched it now reads **"heading over budget"**
instead of **"over budget"**, and flips to "over budget" the moment work starts. Concretely,
at a −50 kronor budget with an hour of work still ahead: amber, *heading 21h 50m over*, while
untouched; red, *over by 1m*, one minute after someone starts. Previously it read red,
*over by 20h 50m*, before anyone touched it.

**3 — What that forced, mechanically** (each folded where it lives, none of it a new decision):
`over_seconds` floors the pot at zero (§5.1); the forecast does not (§3.4, D1 untouched);
`allowed_seconds` is served floored so the app's between-poll ticking still matches the server
(§5.2); §6's two boundary bullets are rewritten and the superseded text preserved (§11 R7-b).

**4 — The second meaning that changed: D10.**
A task with **no work left to come** shows no forecast, whatever its budget. All steps skipped
before production ran ⇒ no time was ever added ⇒ no overrun and no projection. A task with work
still ahead keeps its forecast. Concretely: the 100-kronor item whose steps were all skipped
reads *within budget* and stays quiet; the same item with a step still pending reads amber.

**5 — One consequence worth knowing before you sign.**
The single-task production-time screen shows **no amber on infeasible tasks today** — its
version of this rule cannot express what you decided in D9. So this list will show amber where
that screen shows nothing, until that screen is converged onto this rule. That was previously
described as a free swap and is not one any more (§2.4A). Feasible tasks are unaffected.

**6 — Four judgement calls made on your behalf**, listed at §10.4 under *"Resolved
unilaterally"*: the `no_budget` row's `actual_worked_seconds`, duplicate task ids, row
ordering, and where the serializer is called from. None of the four changes what anyone sees.

**7 — The act.** **No owner decision is open.** Confirming §§2–6 above leaves nothing
outstanding. The header then returns to **RATIFIED** with a §11 round 9 entry naming the owner,
the date and this surface — and only the owner's explicit act writes it. **Silence never
ratifies; the gate holds.**

---

## 11. Shaping changelog

**Round 1 — DRAFT (2026-08-24), Claude Opus 5.** Shaped from the frontend handoff of
2026-08-23 plus a repo inspection of all four item-economics read surfaces, the pure
allocator, the calculator, the price-scenario module, the evaluation table, the router
and its two mirror tests, and the frontend's `buildOutlook` and `buildTaskBudgetOverrun`
at source. Resolutions recorded:

- **S1 (owner, shaping conversation).** Scope is the **frontend read only**. No
  scheduler-ready service shape, no event emission, no transition persistence. Folded
  as §8's deferred list and HC-7.
- **S2 (owner, shaping conversation).** `over_*` and `projected_over_*` are **both
  populated**; `budget_state` names the headline with `over` winning. This *reverses*
  the handoff's own specification (its first open question offered the alternative and
  said the frontend can render it). §2.4 subsequently found the shipped `buildOutlook`
  already behaves this way, which corroborates the choice — recorded because the
  corroboration arrived after the decision, not before it.
- **S3 (owner, shaping conversation).** The work goes through the full pipeline from
  intention-shaper — hence this document.
- **S4 (shaper, repo-derivable).** Roles are **ADMIN/MANAGER only**, resolving the
  handoff's "WORKER/SELLER only if free". The standing decision
  `decision-money-audience-admin-manager-only` requires a withheld monetary key to be
  ABSENT rather than null, which would contradict HC-4's flat non-nullable row and
  force a second serializer. Not free. Folded as HC-3.
- **S5 (shaper, repo-derivable).** The rate is the **committed evaluation's snapshot**,
  not the live basis version `price-scenario` uses. Folded as §4.1. Answers the
  handoff's fifth open question.
- **S6 (shaper, proposal — not yet owner-confirmed).** The pure rule goes in a **new**
  `budget_signal.py` rather than as a function added to `budget_division.py`, so the
  file every shipped read surface depends on is not touched at all. Naming table §7.2.
- **S7 (shaper, measured).** The money contract (§4.2) is a *call*, not a formula.
  Both plausible reimplementations were probed over 20,005 cases and both disagree with
  the shipped figure — the literal inverse of the price-scenario chain on 502 cases,
  the exact single-step rational on 24, all 24 at exact half-ties. This changed the
  contract from "agree with the price-scenario pipeline" (the handoff's wording, which
  is satisfiable but names the wrong authority) to "be the same function call".
- **S8 (shaper, measured — escalated, not resolved).** The two-operand accounting
  divergence (§3.4) was found by deriving the identity
  `Σ participating left ≡ allowed − actual` and then probing it: it holds, **except**
  when an excluded step sits inside an otherwise participating section, where it is off
  by exactly that step's worked seconds. Material — it can manufacture a
  `projected_over` verdict — so it is **owner card 1**, not a shaper resolution.
- **S9 (shaper).** The handoff's open questions 2 (hysteresis) and 3 (per-channel
  floor) are answered in §7.4 and §3.3 respectively: the endpoint serves raw seconds
  and the current verdict; thresholds and dedup belong to whatever fires the event.
  Question 4 (converging `production-time`) is answered as *yes, and it is now cheap*
  (§2.4) but explicitly not scheduled (§8).

Open after round 1: **4 owner cards** (§10). Status stays DRAFT until the owner has
read it; it moves to COLLABORATING on the owner's first response.

**Round 2 — COLLABORATING (2026-08-24), owner response folded.** The owner accepted the
recommendations on cards 1, 2 and 4, and asked for card 3 to be explained because it
conflated a missing valuation with a missing currency.

- **D1 (owner) — card 1: cost the pot side.** `remaining_pot_seconds` is
  `allowed_seconds − actual_worked_seconds`, never `Σ participating left_seconds`.
  Folded as §3.4.
- **D2 (owner) — card 2: `INFEASIBLE` is budget-bearing and reports `over`.** Folded as
  §6, together with the two boundary consequences it forces (zero-worked infeasible
  tasks fall through to `within_budget`; `allowed_seconds` is served negative,
  unclamped).
- **R2-a (shaper, correction) — card 3's round-1 recommendation was fiction.** It
  proposed falling back to "the workspace's configured currency". **There is no
  workspace currency**: `workspaces` carries `name`, `time_zone`, `created_by_id`,
  `created_at` and nothing else. Currency exists on exactly four rows —
  `item_valuations`, `production_cost_basis_versions`, `cost_model_versions`, and the
  `item_cost_evaluations` snapshot that copies them at commit under
  `validate_currency_equality`. The card is rewritten in §10 with three branches that
  exist. **This was caught only because the owner asked for an explanation**, which is
  the collaboration loop doing its job and is recorded as such rather than silently
  repaired.
- **R2-b (shaper, measured) — §3.4 has a second, independent cause.** Answering D1
  prompted a check of what `_budget_seconds` does with a negative allowance. It returns
  a negative integer (`−12.50` min → `−750` s) and `divide_production_budget` floors
  `distributable_seconds` at zero while leaving `budget_seconds` unclamped
  (`budget_division.py:328`). So the section sum and the task pot also diverge for
  infeasible and fully-charged tasks — by `max(0, charged − budget)`, which is
  **unbounded by the excluded steps' worked time**. The round-1 text asserted the delta
  *was* that worked time; that assertion was wrong and §3.4 now states both causes and
  their combined form. D1 is unaffected — it is in fact reinforced, since the pot side
  is the only operand that stays coherent for an infeasible task.
- **R2-c (shaper) — a consequence of D1 that no criterion may overclaim.** D1 removes
  the divergence from this surface by choosing a side; it does not remove it from the
  codebase. Until `production-time` converges (§8, deferred), its `buildOutlook` line
  and this badge can legitimately differ. §3.4 records the expected difference so a
  phase does not grow a criterion asserting an agreement that was never promised.

Open after round 2: **1 owner card** (§10, card 3). Card 4 (ratification) is held
pending it, on the owner's instruction.

**Round 3 — READY_FOR_RATIFICATION (2026-08-24). Shaping closed.**

- **D3 (owner) — card 3: `no_currency`, the first branch, no fallback chain.** Folded
  as §5.1, together with the two things the rule needs to be safe: the member is
  **wire-only** and must not be added to the persisted `ItemCurrencyEnum`, and the
  valuation is deliberately not consulted — partly for the one-rule reason the owner
  chose it for, and partly because in the `CURRENCY_MISMATCH` case the valuation's
  currency is one of three conflicting answers and serving it would name a winner the
  system has explicitly refused to pick.
- **R3-a (owner instruction) — the shaper's role ends at this draft.** The owner
  stated that this session does not continue as coordinator/orchestrator. Two
  consequences, both discharged in this round:
  1. **The ratification surface is written into the document (§10.1)** rather than
     existing only as chat. The charter requires cards to be relayed *verbatim* and
     warns that re-summarising them is how the story dies; a surface that lived only
     in a closed conversation could not be relayed at all.
  2. **§10.2 states the mechanics of recording ratification** — replace the header,
     append a changelog entry naming owner, date and the surface presented — so the
     next actor does not have to re-derive the gate's own protocol from the charter.
- **R3-b (shaper) — what is deliberately left for the next role, and why.** The
  naming registry (§7.2) stays a **proposal**: the charter's artifact map gives the
  naming registry to the master plan, so the planner owns it and confirming it here
  would put the same content in two places. Phase sizing (§9, item 3) likewise names a
  plausible two-phase split without fixing it — that is the planner's call against the
  ≤ 8-criteria rule, not the shaper's.
- **R3-c (shaper) — no artifact folder beyond `planning/` was created.** The
  implementation-folder layout (`plans/`, `prompts/<role>/`, `handoffs/<role>/`) is
  the coordinator's to establish when the project starts moving; creating empty tables
  now would assert a project state that does not exist.

Open after round 3: **0 owner decisions.** Outstanding: **D4, ratification** (§10.2),
which is the owner's act alone.

**Round 4 — artifacts committed and the session closed (2026-08-24).** No semantic
change; the gate does **not** re-open. Recorded because two round-3 statements are now
out of date and the doctrine forbids rewriting them in place.

- **R4-a (owner instruction) — commit, and leave the research behind.** The owner asked
  for this session's grounding to be written down so the next agent does not re-derive
  it. Produced:
  `handoffs/shaper/20260824_shaping_context_handoff.md` — the verified anchor map, the
  facts established, both probes **verbatim and re-runnable**, an explicit list of what
  the session did *not* do, and the collision in R4-c.
- **R4-b — this supersedes R3-c.** R3-c said no folder beyond `planning/` was created.
  `handoffs/shaper/` now exists, holding one real row. The rest of R3-c stands: `plans/`
  and `prompts/<role>/` are still the coordinator's to establish.
- **R4-c — a second frontend handoff collides with HC-2, and the owner has seen it.**
  `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md` asks
  for two additive fields **on `budget-allocations`** — step state and a live per-step
  remaining share — so a worker starting a "36m" step knows the task has 27 minutes
  left. Same overrun problem, worker's side. **HC-2 forbids touching that endpoint**, and
  HC-2 is load-bearing for **M6**. Whether HC-2 survives contact with that request must
  be decided **before phase 1**: relaxing it after a plan exists is a material semantic
  change that re-opens this gate. Not resolved here — the shaper read only its summary,
  and it is a different request with its own shaping ahead of it.
- **R4-d — closing commit `a2fe8b9`** carries this document, the context handoff, the
  appended archgraph observation entry, and the frontend's 2026-08-23 handoff (committed
  alongside so this document's `shaped_from` citation resolves in history). **No code, no
  tests, no graph writes; the suite was never run and no baseline in this project is the
  shaper's.**

**Round 5 — RATIFIED (2026-08-24).** The owner (**David**) ratified the intention on the
**§10.1 surface**, relayed whole: the intended outcome in plain language, the **§1A
measurement ledger verbatim — all six entries, M1–M6, each with its defect family**, the
§8 scope boundaries (ships / does not ship), and the decision index. The answer was
"**Yes — ratify as presented**." Recorded at §10.2.

- **D5–D8 (owner)** — four confirmations taken **before** the ratification question, on
  calls the document had made on the owner's behalf; all four confirmed the text as
  written, no section changes (§10.3). **D5 resolves R4-c**: HC-2 stands, the worker
  time-pressure request is its own project.
- **D4 (owner)** — the ratification act itself.
- **Session note.** The owner said the orchestrator's workflow was already set up
  externally and that this was the owner's first ratification in the agentic flow; the
  session's job was to make the surface understandable, ask the questions that remained,
  and record the act — not to re-open shaping. No mechanism, measurement or scope text
  changed in this round. The gate is open; **mechanism-inventory is next.**

Open after round 5: **nothing.** The intention is authority.

**Round 6 — COLLABORATING (2026-08-24), mechanism-inventory.** Claude Opus 5, planner role,
round 1. The gate check passed on entry — the header read `RATIFIED` and recorded the owner's
2026-08-24 act — and the session then **re-opened the gate on one finding**, per the charter's
post-ratification amendment path. Adversarial inventory of every load-bearing mechanism,
ranked by silent-failure risk; twelve mechanisms reached contract grade as §§3A, 4A, 5A, 6A,
7A. No numbered section was renumbered and no existing sentence was rewritten.

- **D9 (OPEN, §10.4) — the one material finding.** §6's boundary bullet, D2's own sentence and
  §6's unclamped-`allowed_seconds` bullet form an inconsistent triangle whenever
  `allowed_worker_minutes < 0`, which is reachable by construction: `calculate_production_budget`
  returns `min(residual, cap)` with **no floor at zero** (`calculator.py:273`). Measured
  end-to-end (§12A P9): price 100.00 with a 150.00 term commits at `allowed_seconds = -75000`,
  so **zero** logged work reports `over` by 75 000 s costing 5 000 minor units. Not chosen by
  this session; carded, header back to COLLABORATING.
- **R6-a (measured) — the terminal predicate can fail silently and constantly.** A section row's
  `state` is a **`str`**; `TERMINAL_STEP_STATES` is a frozenset of **enum members**, so
  `"completed" in TERMINAL_STEP_STATES` is `False` for every state (§12A P1). HC-6.2's "the
  imported constant, never a locally spelled set" *permits* the failing spelling. §3A.2 pins the
  value-set comparison and names the mutation. This is the highest-value contract of the round.
- **R6-b (measured) — §3.1's "unchanged" was a claim about the callee only.** Passing
  `typicals_by_section=None` to `divide_production_budget` does not raise; it silently returns an
  **equal** split, changing every `left_seconds` and the projection with it. §3A.1 pins all four
  arguments and names the fixture that can observe it.
- **R6-c (measured) — the frontend's acceptance criterion 2 is not satisfiable.** At a typical
  rate the first eight seconds of overrun cost `0` minor units (§12A P11), and D8 gives `over` no
  floor, so `over` with `over_cost_minor == 0` is correct. §4A.3 records it; the `to_frontend`
  handoff must correct it.
- **R6-d — three overclaim guards added**, each of the R2-c family: M2 does not promise this
  row's money equals `budget-status`'s (different durations, same function — §4A.3); M5 does not
  promise `budget_state` constancy on a task with live accrual, and `projected_over` is not
  monotone at all — only `over` is absorbing (§6A.4); this surface's `over_seconds` may differ
  from the sibling's `remaining_worker_minutes` by up to 0.3 s because one is second-domain and
  the other minute-domain (§3A.5).
- **R6-e — §7.3's determinism promise had no mechanism.** The sibling iterates an unordered
  `select(Task)`; §7A.2 supplies the ordering, and names why the obvious two-call test cannot
  fail without a reversed-request fixture.
- **R6-f — HC-2a survives, with one uncounted literal**, and HC-7's "twelve statements" is
  corrected to twelve plus one averaging sweep per user holding an open `WORKING` record
  (§7A.6). Both non-semantic. `Application_contracts` was checked: it publishes **no**
  item-economics endpoint contract, so nothing there needs a row.
- **R6-g — no code, no tests, no graph writes, no suite run.** Graph reads only: `archgraph_status`
  plus three `get_node` calls. `.archgraph/contexts/current-task.md` untouched. The `app/` tree is
  byte-identical to the shaper's probe tree (`git log 4a7cc69..HEAD -- app/` empty), so §12's
  probes were **cited, not re-run** (charter: over-evidence is a defect); §12A's eleven probes are
  new hypotheses at new sites.

Open after round 6: **1 owner decision — D9 (§10.4).** The gate is closed; nothing downstream
compiles until the owner answers and the header returns to RATIFIED.

**Round 7 — COLLABORATING (2026-08-24), D9 answered and folded.** The owner answered D9 with a
reading **neither offered branch carried**, and it is the better one: a negative pot before any
work is a **forecast**, not an incurred fact, because the price was set before the work began;
it becomes a fact the moment someone starts working. Answer quoted verbatim at §10.4.

- **D9 (owner) — folded** as §6A.3, and into §5.1 (`over_seconds` floors the pot), §5.2
  (`allowed_seconds` is served floored), §6 (both boundary bullets rewritten, rank 3 gains a
  conjunct), §3.4 (a note that D1 is untouched) and §3A.4 (the arithmetic block, with two named
  mutations for the two clamps). The superseded round-5 text is preserved below.
- **R7-a — what D9 did *not* touch, stated so nothing is re-litigated.** **D1 stands**: the
  projection's second operand is still the unclamped task pot, and the deficit therefore enters
  the forecast at full size — which is what makes the owner's "already projected to be
  overbudget" true rather than merely asserted. **The §1A measurement ledger is untouched**:
  all six outcomes read exactly as ratified in round 5, and M1's wording already covers the new
  case. **D2 stands and is now literally true** for the first time — with the pot floored for
  the incurred figure, an infeasible task's first logged minute makes it `over` by exactly the
  full worked time, which is what D2 always said and what the round-5 arithmetic did not deliver.
- **R7-b — the superseded round-5 text**, preserved because it is what the owner ratified:
  *"an `INFEASIBLE` task with **zero** worked seconds is `within_budget`, not `over` —
  `over_seconds` is `max(0, actual − allowed)` and both are zero, so the rank falls through"*
  and *"`allowed_seconds` … is served as-is, not clamped: it is the pot the frontend
  extrapolates against, and clamping it to zero would make the client's forward extrapolation
  disagree with the served `over_seconds`."* The first was false whenever the allowance was
  strictly negative; the second's *reason* is honoured by D9 and its *instruction* reversed,
  because the reason binds to whatever `over_seconds` actually subtracts.
- **R7-c — transcribing "the moment the task transitions to working".** Bound to
  `actual_worked_seconds > 0`, not to "a step is in `WORKING`" (§6A.3). The two coincide at the
  instant the owner described and diverge afterwards, where the seconds reading is the correct
  one — a task worked yesterday and now paused is still an incurred fact. Recorded because a
  paraphrased owner sentence becoming a criterion is a defect family this lineage has paid for.
- **R7-d (new, D10 §10.5) — D9's answer created one small open question.** The shipped
  `buildOutlook` gates its projection on `remaining_commitment > 0` before applying the floor;
  round 1 of this document transcribed the floor and **dropped the guard**. Under the round-5
  arithmetic the omission was inert. D9 makes it load-bearing: a task with nothing left to do
  but a negative pot would forecast an overrun that can no longer happen. Not chosen here —
  restoring a guard the frontend has and this document lost is still a change to what a
  manager sees, so it is carded.
- **R7-e — probe P12** (§12A) works the ruled rule through eight fixtures, four infeasible and
  four feasible, and confirms the 60-second floor and every feasible verdict are **unchanged**.
  No code, no tests, no graph writes, no suite run in this round either.

Open after round 7: **1 owner decision — D10 (§10.5)**, plus the re-ratification act itself.

**Round 8 — COLLABORATING (2026-08-24), D10 answered; and this round corrected its own
previous round.** The owner answered D10 by reasoning from the domain rather than from the
card — *"if all the task steps where skipped before production ran then there is not aditive
time that is placed on the budget thus no over budget nor projection happens"* (§10.5,
verbatim) — and asked whether that resolved the conflict.

- **D10 (owner) — it resolves it, and the reasoning checks out at the source.** With every step
  skipped, every section returns `share_state == "excluded"` and `left_seconds is None`, so the
  contributing set is empty and no time reaches either figure. Skipped work is not additive.
- **R8-a — the round-7 card named the wrong mechanism for the right distinction, and this round
  found it by deriving what it had previously assumed.** D10's branch A was written as
  `remaining_commitment > 0`. Running the real `divide_production_budget` over seven infeasible
  shapes showed `remaining_commitment` is **identically `0` on every infeasible task**: §3.4
  cause 2 floors `distributable_seconds` at `max(0, budget − charged)`, so under a non-positive
  budget every section allowance is `0` and every `left_seconds` is `≤ 0`. That conjunct would
  have returned `within_budget` for the untouched task with real work ahead — **deleting D9's
  verdict one round after the owner made it.** Corrected to a **contributing-set emptiness
  test** (§3.3, §3A.4, §6A.2), which is what the owner's sentence actually distinguishes.
- **R8-b — how the defect got in, recorded because it is the lineage's own named family.**
  Round 7's probe P12 **supplied** `commitment = 3600` as a fixture parameter instead of
  deriving it from the allocator. A hand-built number that the production path cannot produce
  is the row-that-cannot-fail shape moved one step upstream, into the evidence a contract was
  written from. §12A's P12 is replaced with a fully derived table, and §3A.4 now warns the
  fixture author explicitly: under a negative pot, a section row with positive `left_seconds`
  is a state the allocator cannot emit.
- **R8-c — §2.4's convergence promise is qualified (new §2.4A).** `buildOutlook` uses the sum
  form of the guard, so `production-time` shows **no amber on any infeasible task today**. D9
  is therefore new behaviour, deliberately chosen, and converging `production-time` onto this
  rule later is no longer the zero-behaviour-change swap §2.4 described. Feasible tasks are
  unaffected.
- **R8-d — nothing else moved.** D1–D9 stand. The §1A ledger stands verbatim. Every **feasible**
  task's verdict is byte-identical under both guard forms (§12A P12, last three rows), so the
  correction touches only infeasible tasks. No code, no tests, no graph writes, no suite run.

Open after round 8: **no owner decisions.** The only outstanding act is **re-ratification**
itself, on the surface at §10.6.

**Round 9 — RATIFIED (2026-08-24).** The owner (**David**) re-ratified the intention on
the §10.6 diff surface after it was relayed in full. The explicit answer was **"yes"**.
That act confirms, without reopening the round-5 authority, the two material amendments:

- **D9:** a negative pot before work is a forecast (`projected_over`), becoming an
  incurred `over` only when `actual_worked_seconds > 0`; the incurred and served-pot
  paths floor zero while the forecast continues to use D1's unclamped task pot.
- **D10:** no contributing work ahead means no forecast; the guard is the
  contributing-set emptiness test, not the infeasible task's always-zero commitment sum.

The owner also saw the stated production-time divergence for infeasible tasks and the
four non-visible contract resolutions at §10.6. No owner decisions remain open. The
header is restored to `RATIFIED`; mechanism-inventory is complete and
implementation-planner is the next role.

**Round 10 — RATIFIED, non-semantic planner fold-back (2026-08-24).** The coordinator
folded planner findings F1, F2 and F6 into the intention's contract authority without
changing any product meaning: §6A.2A replaces the unreachable row 4 and stale
`remaining_commitment` guard wording with the derived reachable-row/set-guard rule;
§4A.1A pins 40 seconds as the two-step-inverse witness; and §6A.1A marks the
no-evaluation detailed-status computation structurally held. These are precision and
observability corrections, not a material semantic amendment; the round-9 ratification
stands and the header remains `RATIFIED`.

---

## 12. Probe record (evidence behind §3.4 and §4.2)

Both probes ran this session against the pure domain modules, no database, on the tree
at `4a7cc69` plus the untracked files listed in `git status`. They are **shaping
evidence, not test coverage** — the plans will own the criteria that pin these
behaviours.

- **§3.4 divergence, cause 1 (round 1).** `divide_production_budget` called with three
  fixtures (`allowed = 60.00` minutes): clean, wholly-excluded-section, and
  excluded-step-inside-participating-section. Deltas `0`, `0`, `−300` as tabulated.
- **§3.4 divergence, cause 2 (round 2).** `_budget_seconds(Decimal("-12.50"))` → `−750`;
  `_budget_seconds(Decimal("0.00"))` → `0`. `divide_production_budget(Decimal("-12.50"),
  [one WORKING step, 300 s])` → `budget_seconds −750`, `charged_seconds 0`,
  `distributable_seconds 0` (floored), single section `allowance_seconds 0`,
  `left_seconds −300`, `share_state over_share`. Delta `+750`, from the floor alone,
  with no excluded step present.
- **§4.2 money.** 5 rates × 4001 durations = 20,005 cases, comparing
  `calculate_consumed_cost_minor` against (a) the exact single-step integer half-even
  and (b) the literal two-step inverse of the price-scenario chain. Mismatches: 24 and
  502. All 24 of (a)'s mismatches verified to satisfy
  `(seconds × rate_ten_thousandths) mod 600 000 == 300 000` — exact half-ties.

---

## 12A. Probe record — mechanism-inventory, round 6 (evidence behind §§3A–7A)

Eleven probes, all against the **pure domain and calculator**, no database, from `backend/app/`
with `PYTHONPATH=. .venv/bin/python`. Tree identity: `f376928`, working tree carrying only the
untracked docs listed in `git status`; `git log 4a7cc69..HEAD -- app/` is **empty**, so §12's
shaping probes remain valid on this tree and were deliberately **not** re-run. These are
mechanism evidence, not test coverage — the plans still own the criteria.

| # | Hypothesis | Observed | Feeds |
|---|---|---|---|
| **P1** | a section row's `state` is an enum member | **`str`.** `"completed" in TERMINAL_STEP_STATES` → `False`; `in {s.value for s in …}` → `True`; `_step_state_is_terminal(section_row)` → `True` (it reads `Mapping`s) | §3A.2 |
| **P2** | a task with no steps crashes the allocator | `sections == []`, `steps == []`, `distributable_seconds == budget_seconds`; no crash | §3A.6 |
| **P3** | every step excluded | both sections `share_state == "excluded"`, `left_seconds is None`; `distributable_seconds == 2700` allocated to nobody | §3A.6, §3A.3 |
| **P4** | `allowed_worker_minutes=None` | `budget_seconds`/`charged_seconds`/`distributable_seconds` all `None`; section `left_seconds is None`, `share_state == "no_budget"`, `state == "working"` | §3A.1, §5A.2 |
| **P5** | `blocked`/`paused`/`pending` sections are terminal | all three non-terminal with `left_seconds` an `int` (1200 each) | §3A.3 |
| **P6** | `_budget_seconds` can hit a half-even tie on persisted allowances | **no.** For `Numeric(12,2)` minutes, `minutes × 60 = 3n/5` is never a half-integer (checked over every 2-dp residue). Rounding is still exercised (`0.01 → 1`, `0.02 → 1`); ties are not. `_budget_seconds(Decimal("-12.50")) == -750` | §3A.5 |
| **P7** | `calculate_consumed_cost_minor` coerces its inputs | **no — it rejects them.** `bool`/`float`/`Decimal` seconds → `TypeError`; `float`/`int`/`None` rate → `TypeError`. `(-60, 3.7500)` → `-4`: **no sign guard**. `(60, Decimal("0.0000"))` → `0` | §4A.1 |
| **P8** | `int(rate.scaleb(4))` can truncate at `Numeric(12,4)` | **no.** `3.7500→37500`, `0.0001→1`, `99999999.9999→999999999999`, `12.3456→123456`, `0.9999→9999` — exact | §4A.2 |
| **P9** | a **negative** production budget is unreachable | **reachable.** `calculate_production_budget(10000, [15000])` → `-5000` (`min(residual, cap)`, no floor); `calculate_allowed_worker_minutes(-5000, 4.0000)` → `-1250.00`; `_budget_seconds` → `-75000`. Zero worked seconds ⇒ literal `over_seconds = 75000`, `over_cost_minor = 5000`. 60 worked seconds ⇒ `75060`, where D2's sentence names `60` | **§6A.3 / D9** |
| **P10** | the minute-domain `remaining_worker_minutes` is a safe source for `over_seconds` | **no.** `allowed 60.00`: `3599 s` → `+0.02` min (1.2 s) vs true 1 s; `3601 s` → `-0.02` min vs true 1 s; `3618 s` → `-0.30` min vs true 18 s. Error up to ±0.3 s, and a `Decimal` | §3A.5 |
| **P11** | `over ⇒ over_cost_minor > 0` | **false.** Cost is `0` for `over_seconds` 1..8 at rate `3.7500`, 1..2 at `12.3456`, 1..30 at `0.9999`; only `41.6667` costs from 1 s | §4A.3 |

**P12 (rounds 7–8) — the ruled rule, worked through with every figure DERIVED.** The round-7
version of this probe supplied `remaining_commitment` as a fixture parameter; round 8 replaced
it with `divide_production_budget` output, which changed the conclusion (§11 R8-a/R8-b). Twelve
shapes, `allowed = -12.50` min (`-750` s) for the infeasible set and `60.00` min for the
feasible set:

| Fixture | contributing sections | commitment | `over` | `projected` | sum-guard verdict | **set-guard verdict (shipped)** |
|---|---|---|---|---|---|---|
| infeasible, untouched, one `pending` step | **1** | `0` | `0` | `750` | `within_budget` ✗ | **`projected_over`** |
| infeasible, untouched, `working` + `pending` | **2** | `0` | `0` | `750` | `within_budget` ✗ | **`projected_over`** |
| infeasible, 60 s logged, work still ahead | 2 | `0` | `60` | `810` | `over` | **`over`** |
| infeasible, **all skipped, never worked** | **0** | `0` | `0` | `750` | `within_budget` | **`within_budget`** |
| infeasible, all skipped, 500 s logged first | 0 | `0` | `500` | `1250` | `over` | **`over`** |
| infeasible, all completed, finished | 0 | `0` | `400` | `1150` | `over` | **`over`** |
| infeasible, no steps at all | **0** | `0` | `0` | `750` | `within_budget` | **`within_budget`** |
| feasible, untouched, work ahead | 1 | `3600` | `0` | `0` | `within_budget` | `within_budget` |
| feasible, heading over | 1 | `1800` | `0` | `1200` | `projected_over` | `projected_over` |
| feasible, 1 s past the pot, all done | 0 | `0` | `1` | `1` | `over` | `over` |
| feasible, commitment exceeds pot by 60 s | 1 | — | `0` | `60` | `projected_over` | `projected_over` |
| feasible, commitment exceeds pot by 59 s | 1 | — | `0` | `59` | `within_budget` | `within_budget` |

**Three things this table establishes.** (1) `remaining_commitment` is `0` on **every**
infeasible row, so the sum form of the D10 guard cannot separate "work ahead" from "nothing
left" and marks the two ✗ rows wrongly. (2) The contributing-set form separates them exactly as
the owner's sentence does. (3) **Every feasible row is identical under both forms**, and the
60/59 floor still bites exactly where D6 put it — the correction touches infeasible tasks only.

P1–P8 and P10–P12 are re-runnable from the scripts recorded in the round-6 handoff
(`handoffs/planner/20260824_mechanism_inventory_round_1.md`); P9 is four calculator calls
reproduced verbatim in the table above.
