# Intention: Task Budget Overrun Signal (one batched verdict read for the managers task list)

```
status: **READY_FOR_RATIFICATION** (round 3, 2026-08-24). **NOT RATIFIED — this header
        is the shaper's *claim*, not the owner's answer. Nothing here is authority yet
        and no downstream skill may compile against it.**
        **0 owner decisions open.** D1 (§3.4), D2 (§6) and D3 (§5.1) are answered and
        folded. The one act outstanding is **D4, the ratification itself** — the
        surface is written into **§10.1** so it can be relayed verbatim by whoever
        next sits with the owner. §10.2 says exactly how to record the answer.
        **⚠ THE SHAPING SESSION IS CLOSED.** The owner ended the shaper's role at this
        draft (§11 round 3); this document is complete and self-contained by design,
        and the pipeline's interface from here is artifacts, never conversation.
        **Next actor: whoever presents §10.1 to the owner.** On RATIFIED →
        mechanism-inventory (§9 lists what it must reach contract grade).
        **⚠ Section-letter precedence:** §3.4 supersedes its own round-1 wording — a
        second, independent cause of the divergence was found in round 2 and a bound
        stated on one cause alone was wrong.
role: intention (pipeline root artifact)
shaped_from: docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md
             (the frontend's request, authored by the frontend's Claude Opus 5 agent)
             plus owner decisions taken in the shaping conversation of 2026-08-24
             (S1–S3 round 1; D1–D2 round 2; D3 round 3; §11).
date: 2026-08-24
round: 3
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

signalled as `projected_over` only when `projected_over_seconds >= 60`. The 60-second
floor exists because the frontend's `formatWorkSeconds` floors to minutes and a smaller
gap announces itself as "0m over". **The floor gates the state, not the figure** — the
raw seconds are always served, so a future notification channel can set its own,
higher bar without a contract change. This answers the handoff's third open question.

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

**Still a rule-6 mechanism.** D1 answers *which operand*, not *how it is proven*. The
required test shape is a fixture carrying an excluded step inside a participating
section, asserting the verdict follows the pot side — a fixture without that step
cannot distinguish D1 from its alternative and is a row that cannot fail.

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

## 5. Domain model — the row, and who owns every field

One flat row per visible task. **No nested array at any depth** (M4).

### 5.1 Authoritative — rendered as served, quotable verbatim by a future notification

| Field | Type | Default | Owner / derivation |
|---|---|---|---|
| `task_id` | string | — | fact: `tasks.client_id` |
| `budget_state` | enum | `no_budget` | **derived**, §6 — the headline verdict |
| `over_seconds` | int ≥ 0 | `0` | derived: `max(0, actual_worked_seconds − allowed_seconds)` |
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
| `allowed_seconds` | int | `0` under `no_budget` | derived: `_budget_seconds(allowed_worker_minutes)` — **the same integer the allocator uses as `budget_seconds`** (`budget_division.py:69`), never a second rounding of the minute figure |
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

## 6. `budget_state` — the complete order

Four members. The order is total and stated in full, because downstream criteria will
enumerate it (charter: if the product ranks anything, the intention states the complete
order):

| Rank | Member | Condition |
|---|---|---|
| 1 | `no_budget` | the task is **not budget-bearing** — no current committed evaluation, i.e. economics status outside `{OK, INFEASIBLE}` (D2) |
| 2 | `over` | budget-bearing **and** `over_seconds > 0` |
| 3 | `projected_over` | budget-bearing, not `over`, and `projected_over_seconds >= 60` (§3.3) |
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

- an `INFEASIBLE` task with **zero** worked seconds is `within_budget`, not `over` —
  `over_seconds` is `max(0, actual − allowed)` and both are zero, so the rank falls
  through. This is the boundary row; a fixture that only ever gives infeasible tasks
  worked time cannot observe it.
- `allowed_seconds` may be **negative** for an infeasible task (`_budget_seconds` of a
  negative Decimal). It is served as-is, not clamped: it is the pot the frontend
  extrapolates against, and clamping it to zero would make the client's forward
  extrapolation disagree with the served `over_seconds`. `over_seconds` itself stays
  `≥ 0` by its own `max(0, …)` (§5.1).

**Why an enum rather than nullability**, recorded because it is a contract and not a
style preference: a future notification fires on **transitions of this field**, not on
levels; it gives the frontend an exhaustive switch that breaks the typecheck when a
member is added; and it separates "not over" from "no budget at all" without a second
field.

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

## 10. Owner decisions — ⚠ **0 OPEN** — and the ratification surface

**All four round-1 cards are answered.** Each decision lives in the section it governs,
per the artifact map; they are indexed here, not restated:

| ID | Decision | Answered | Lives in |
|---|---|---|---|
| **D1** | The projection subtracts the **task** pot (`allowed − actual`), never the section sum | owner, 2026-08-24 | §3.4 |
| **D2** | `INFEASIBLE` is budget-bearing and reports `over`; `no_budget` means "we cannot say" | owner, 2026-08-24 | §6 |
| **D3** | `currency` gains a wire-only fourth member `no_currency`; no fallback chain | owner, 2026-08-24 | §5.1 |
| **D4** | Ratification — **the one act still outstanding**, below | pending owner | this section |

Shaping resolutions the owner did not need to arbitrate (repo-derivable, each with a
rationale in §11): **S4** roles, **S5** rate source, **S6** naming, **S7** money is a
call, **R2-a** the workspace-currency correction, **R2-b/c** the second divergence cause.

---

### 10.1 The ratification surface (presented to the owner; **not yet answered**)

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

### 10.2 D4 — the ratification act

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
