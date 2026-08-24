---
plan: planning (project-level — belongs to no phase)
role: planner (mechanism-inventory doctrine)
round: 1 (+ addenda §8 and §9, written after the owner answered D9 and D10 in the same session)
date: 2026-08-24
state: ALL OWNER DECISIONS ANSWERED (D1–D10) AND FOLDED — intention at COLLABORATING pending
       the re-ratification act alone
verdict: mechanism-inventory exit gate PASSED on substance — every silent-failure mechanism
         carries a contract and nothing is marked OPEN — but the pipeline gate is the
         intention header, which is not yet RATIFIED
actor: Claude Opus 5 (1M context), mechanism-inventory role
---

# Mechanism-inventory round 1 — Task Budget Overrun Signal

## Summary

The gate check passed on entry: the intention read `status: **RATIFIED**` and recorded the
owner's 2026-08-24 act, so the session proceeded. Twenty-two load-bearing mechanisms were
inventoried and ranked by silent-failure risk; **twenty-one of them now carry contract-grade
definitions** in the intention, written as five new lettered sections (§§3A, 4A, 5A, 6A, 7A).
Those sections contribute twenty-two rows to the §1A registration table — one per contract
that serves a measurement, including the open one and excluding §7A.7, which is a pattern
note rather than a mechanism. No numbered section was renumbered and no
existing sentence was rewritten.

**The twenty-second re-opened the gate.** §6's own boundary bullet, D2's own sentence, and
§6's unclamped-`allowed_seconds` bullet form an inconsistent triangle whenever
`allowed_worker_minutes < 0` — and that is reachable by construction, not by corrupt data:
`calculate_production_budget` returns `min(residual, cap_minor)` with **no floor at zero**
(`calculator.py:273`). Measured end to end (probe P9): an item priced `100.00` carrying one
`150.00` cost-model term commits at `production_budget_minor = -5000`, `allowed_worker_minutes
= -1250.00`, `allowed_seconds = -75000`. A task with **zero** logged work then reports
`budget_state: "over"`, `over_seconds: 75000`, `over_cost_minor: 5000`. Choosing which half of
the ratified text survives changes what a manager sees and what money is named, so this
session did not choose it. Intention header → `COLLABORATING`; card **D9** below and at
intention §10.4.

**The owner answered D9 in the same session, with a reading neither offered branch carried.**
It is folded; see the round-7 addendum at §8, which supersedes the "next gate" of §7 and is the
part of this handoff to read first. **One decision remains open (D10)**, and it is a
consequence D9's own answer created.

**Next actor is still NOT implementation-planner.** It is the coordinator, relaying D10 and the
re-ratification surface (intention §10.6) to the owner.

---

## ⚠ OWNER DECISIONS REQUIRED (0)

**Nothing needs an owner decision.** D9 and D10 were both raised, answered by the owner and
folded within this session (§8 and §9). The only outstanding act is **re-ratification** —
the owner's explicit signature on the surface at intention §10.6. Both cards are retained
below marked ANSWERED, because the record of what was asked is what makes the answer
readable later.

### D10 — no work left to come, no forecast (**ANSWERED 2026-08-24; the card's own mechanism was wrong — see §9**)

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

**Trace:** §3.3; §6 rank 3; §3A.4; §6A.2; M1, M3.

**ANSWERED (owner, David, 2026-08-24) — branch A, reasoned from the domain rather than from
the card.** Verbatim:

> *"the thing is that if all the task steps where skipped before production ran then there is
> not aditive time that is placed on the budget thus no over budget nor projection happens.
> does that solve the conflict or perhaps im not understanding the problem enterely"*

It solves it, and the reasoning is correct at the source. **But this card named the wrong
mechanism for the owner's right distinction, and §9 records the correction.**

---

### D9 — the negative-allowance boundary (**ANSWERED 2026-08-24; retained for the record**)

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

**ANSWERED (owner, David, 2026-08-24) — a third reading the card did not carry.** Verbatim:

> *"about the owner card, the recommendation holds part of the answer, yes the moment the
> task transitions to working it becomes over budget, but before transitioning to working it
> displays a projection, because the user has placed the price and before some one even works
> the task is already projected to be overbudget, the moment someone starts working with it
> then it is a fact that is over budget."*

Branch B was right that an untouched task must not read `over`, and wrong that it should read
`within_budget`: the deficit is **known in advance**, which is exactly what a projection is
for. Folded — see §8.

---

### Resolved unilaterally by contract — listed for owner ratification, no card

Four internal imprecisions were resolved without changing any meaning the document already
carried. Each is recorded in the section it governs and repeated at intention §10.4 so the
owner ratifies them alongside D9. Deciding which side of an imprecision wins can carry
consequences even when no sentence changes, which is why they are surfaced rather than folded
silently.

1. **§5A.2** — under `no_budget`, `actual_worked_seconds` is served as `0` rather than as the
   task's real live figure. §5.2's table qualifies two of its three fields with "`0` under
   `no_budget`" and leaves this one bare. Both readings render identically (nothing on a
   `no_budget` row is drawn), and the sibling sets the analogous field to `None` on the same
   branch.
2. **§7A.1** — M4's "N tasks → N flat rows" is read as *one row per **distinct** visible
   requested id*. Duplicate ids collapse inside `Task.client_id.in_(task_ids)`; the sibling
   has behaved this way since it shipped.
3. **§7A.2** — row ordering is `task_id` ascending. §7.3 already promised determinism; the
   sibling it mirrors does **not** implement it (unordered `select(Task)`), so the promise had
   no mechanism.
4. **§7A.7** — the serializer is called from the service, matching the sibling, rather than
   from the router as architecture contract `46_serialization.md` prescribes. HC-2 forbids
   touching the surface being mirrored, so consistency with it wins; recorded with its reason
   so a reviewer does not file it as a finding.

---

## 1. The ranked inventory

Ranked by the mechanism-inventory question — *"if this is subtly wrong, does anything crash,
or does the system quietly behave wrong forever?"* — not by apparent complexity.

| # | Mechanism | If subtly wrong | Risk | Contract |
|---|---|---|---|---|
| 1 | **The "still to come" predicate's membership test** — a section row's `state` is a `str`, `TERMINAL_STEP_STATES` is a frozenset of enum members | the predicate is **constantly true**: every section, including every completed one, counts as still to come; `projected_over_seconds` inflates by the task's whole finished commitment and amber badges appear on tasks finishing on time. Nothing raises; nothing else in the repo reddens | **critical** | **NEW §3A.2** |
| 2 | **The allocator call's `typicals_by_section` argument** | passing `None` does not raise — `apply_business_fallback` weights every section `Fraction(1,1)`, so the allocator returns an **equal split**. Every `left_seconds` changes and this badge silently disagrees with the workers-app step cards computed from the same allocator | **critical** | **NEW §3A.1** |
| 3 | **The negative-allowance, zero-work boundary** | a task nobody has touched shows a red over-budget badge with real money attached, forever | **critical** | **OPEN — D9 / §6A.3** |
| 4 | **Money is a call, and its input types** | `calculate_consumed_cost_minor` rejects `bool`/`float`/`Decimal` seconds and non-`Decimal` rates with `TypeError`, which `run_service` converts into a generic **HTTP 500** — the whole page of 25 fails with no identity. It also has **no sign guard**: negative seconds yield negative money | **high** | §4.2 existed; **NEW §4A.1** |
| 5 | **The per-section clamp, applied before the sum** | summing first and clamping once is a one-character edit and is exactly the quiet cancellation M3 exists to guard | **high** | §3.3 existed; **NEW §3A.4** |
| 6 | **Second-domain vs minute-domain operands** | reusing the sibling's `remaining_worker_minutes` *looks* like the reuse HC-6 asks for; it is a `Decimal` carrying up to ±0.3 s of quantization error | **high** | **NEW §3A.5** |
| 7 | **Row ordering** | §7.3 promises determinism; the sibling iterates an unordered `select(Task)`. A two-call test passes without any ordering, because a small table seq-scans in physical order | **high** | **NEW §7A.2** |
| 8 | **The `no_budget` row** | a future change to the allocator's no-budget branch could leak a non-zero figure onto a row whose state says there is no budget | med-high | **NEW §5A.2** |
| 9 | **The state decision procedure, rows 3 and 6** | a criterion set enumerating only rows 1/2/5/7 looks exhaustive and never observes a `within_budget` row carrying a sub-floor projection, or an `over` row carrying a populated projection | med-high | §6 existed; **NEW §6A.2** |
| 10 | **`no_currency` staying wire-only** | adding it to `ItemCurrencyEnum` needs a migration on `item_valuation_currency_enum` (HC-1 forbids) and puts a value in the type no row can hold | medium | **NEW §5A.3** |
| 11 | **What M5 actually promises** | `budget_state` is *not* constant on a task with live accrual, and `projected_over` is not monotone at all — only `over` is absorbing. A criterion asserting projected-state stability asserts something the design does not promise | medium | **NEW §6A.4** |
| 12 | **A non-zero overrun costing `0`** | at rate `3.7500` the first **eight** seconds of overrun cost nothing. The frontend's acceptance criterion 2 (`over_cost_minor > 0`) is **not satisfiable** | medium | **NEW §4A.3** |
| 13 | **Batch cardinality, duplicates, visibility** | `len(rows) == len(task_ids)` is false for a duplicate-bearing request; dropping the `is_deleted` clause silently returns deleted tasks | medium | §7.3 existed; **NEW §7A.1** |
| 14 | **Error identity and the two 422 envelopes** | the identity is a **prefix of the `error` string**, not a code field; and a missing `task_ids` param returns FastAPI's `{"detail": …}` 422, a different envelope the frontend must not assume | medium | **NEW §7A.3** |
| 15 | **Rate scaling exactness** | `int(rate.scaleb(4))` is exact only because the column scale is 4; `int()` truncates toward zero, so a scale change would start rounding down silently | medium | §4.1 existed; **NEW §4A.2** |
| 16 | **budget-bearing ⟺ a current committed evaluation** | §5.1's "guaranteed present" is a real theorem on the production path, not an assumption — and the unique partial index guarantees the `{task_id: evaluation}` map cannot drop a duplicate | medium | §6/D2 existed; **NEW §6A.1** |
| 17 | **The eight-member step-state partition** | `completed` is terminal but **not** excluded — the reason a finished section still holds a budget slice. `TERMINAL_STEP_STATES ≠ EXCLUDED_STEP_STATES` | medium | **NEW §3A.3** |
| 18 | **Allocator totality on this rule's paths** | prevents both a defensive branch for an impossible case and a missing one for a possible case; there is no zero-division path | low | **NEW §3A.6** |
| 19 | **Route precedence** | no bare `GET /tasks/{param}` exists today, so placement is the durable guard rather than the current fix | low | §7.1 existed; **NEW §7A.4** |
| 20 | **The authorization boundary** | satisfied by construction (route gate, no worker variant), not by field filtering — an `include_monetary` flag would be the mechanism `decision-money-audience-admin-manager-only` explicitly rejected | low | HC-3 existed; **NEW §7A.5** |
| 21 | **HC-2a's artifact set and HC-7's query count** | HC-2a holds at four artifacts, but artifact 1 carries an uncounted literal (the test **function name** `test_the_registry_ships_twenty_six_routes`). HC-7's "twelve statements" is twelve **plus one averaging sweep per user holding an open `WORKING` record** | low | **NEW §7A.6** |
| 22 | **Serializer placement** | the item-economics batch surfaces already deviate from `46_serialization.md`; carried forward with its reason | low | **NEW §7A.7** |

**Exit-gate status: NOT passed.** Rows 1–2 and 4–22 are contract grade. Row 3 cannot be
written without the owner.

---

## 2. Intention deltas, with their ledger registrations

All writes are additive lettered sections; **no numbered section was renumbered** and no
existing sentence was rewritten (charter citation-stability rule). Twenty-two rows were
appended to §1A's mechanism-contract registration table.

| Delta | What it fixes | Registers against |
|---|---|---|
| **§3A.1** the allocator call | §3.1's "unchanged" was a claim about the callee only; all four arguments are now pinned, with the fixture that can observe the `typicals` mutation | M1, M6 |
| **§3A.2** the terminal predicate | types of `state`/`left_seconds`; the value-set comparison; **two** forbidden spellings, not one; named mutation on the definition | M1 |
| **§3A.3** the step-state partition | all eight members × both frozensets × section effect × pot effect | M1, M3 |
| **§3A.4** clamp and floor | int-only arithmetic; clamp *inside* the sum; `59/60` adjacent pair; three named mutations, one per sub-check | M3, M1 |
| **§3A.5** second-domain operands | forbids deriving either operand from `remaining_worker_minutes`; records the ≤0.3 s expected divergence as an overclaim guard | M1, M2 |
| **§3A.6** allocator totality | four input shapes; no zero-division path | M1 |
| **§4A.1** Q5 call identity | exact accepted types; the `run_service` 500 consequence; absence of a sign guard; the prohibited derivations named for grep | M2 |
| **§4A.2** rate scaling | exactness from column scale; committed rate is never zero | M2 |
| **§4A.3** zero-cost overrun | corrects the frontend's acceptance criterion 2; narrows M2 to what it promises | M2 |
| **§5A.1** row types | per-field production type and JSON form; **no `Decimal`, no string-encoded numbers** on this wire | M4 |
| **§5A.2** the `no_budget` row | constructed from constants, not computed; resolves §5.2's ambiguity | M4 |
| **§5A.3** `no_currency` | derived vocabulary; the sentinel appears once; the absence claim ships with a probe that can observe the presence (charter rule 15) | M4 |
| **§6A.1** budget-bearing | the equivalence proven on the production path; the unique partial index | M4 |
| **§6A.2** decision procedure | seven exhaustive rows; rows 3 and 6 named as the ones a plan forgets; three named mutations | M4 |
| **§6A.3** the boundary | **OPEN — D9** | M4 |
| **§6A.4** stability | the invariant/free-to-move partition; `over` is absorbing, `projected_over` is not | M5 |
| **§7A.1** batch semantics | cap before dedup; duplicates collapse; three-clause visibility predicate; 50/51 adjacent pair | M4 |
| **§7A.2** ordering | one place only; the reversed-request fixture that can actually fail | M5 |
| **§7A.3** error identity | prefix-not-code; 422 vs FastAPI's own 422; the generic-500 catch-all | M4 |
| **§7A.4** mounting | declared immediately after the sibling | M6 |
| **§7A.5** authorization | by construction; no `include_monetary` flag | M6 |
| **§7A.6** HC-2a / HC-7 | four artifacts confirmed + the uncounted literal; three further tripwire families cleared; query count corrected | M6 |
| **§7A.7** serializer placement | the pattern deviation carried with its reason | — |
| **§10 / §10.4** | heading, D9 index row, the card verbatim, the four unilateral resolutions | — |
| **§11 round 6** | the changelog: D9 plus R6-a…R6-g | — |
| **§12A** | eleven probes, tree-identified and re-runnable | — |
| **header / frontmatter** | `RATIFIED → COLLABORATING`, round 5 → 6, section-letter precedence extended | — |

---

## 3. Source evidence inspected

**Read at source this session** (all on `f376928`): `budget_division.py` (whole file, 418
lines), `calculator.py` (`_guard_type`/`_require_*`, `calculate_production_budget`,
`calculate_allowed_worker_minutes`, `calculate_consumed_cost_minor`,
`calculate_actual_worker_minutes`, `calculate_remaining_worker_minutes`),
`get_task_budget_allocations.py` (whole file), `get_task_budget_status.py:180-215`,
`get_task_price_scenario.py:296-299`, `live_worked_seconds.py` (whole file),
`division_serializers.py` (whole file), `typical_filters.py:329-344`,
`routers/api_v1/item_economics.py` (route list, `_run`, `_ctx`, `_run_budget_status`,
`:318-400`), `services/run_service.py`, `services/context.py`, `routers/http/response.py`,
`errors/base.py`, `errors/validation.py`, `domain/task_steps/constants.py`,
`domain/task_steps/enums.py`, `domain/items/enums.py`, `domain/item_economics/enums.py`,
`models/tables/item_economics/item_cost_evaluation.py`,
`commit_item_cost_evaluation.py:295-325`,
`app/tests/unit/routers/test_phase9_item_economics_route_mirror.py`,
`app/tests/unit/routers/api_v1/test_item_economics_router.py`,
`app/tests/unit/docs/test_item_economics_docs.py`,
`app/tests/unit/docs/test_item_economics_handoff_accuracy.py`,
`app/beyo_manager/routers/README.md` (header, quick index, the sibling's detail section),
`Application_contracts/backend/architecture/46_serialization.md`.

**Probes — eleven, all new hypotheses at new sites.** Recorded as intention §12A; the two
scripts are reproduced in §5 below. Tree identity: `f376928`, working tree carrying only the
untracked documents in `git status`.

**Evidence deliberately NOT re-run.** `git log 4a7cc69..HEAD -- app/` is **empty**, so the
shaper's §12 probes are tree-valid on this tree and were cited rather than reproduced
(charter: re-running evidence whose tree identity matches yours, with no variation, is a
finding against the session). **The test suite was not run at all** — this is a
contract-definition session; no baseline in this project is this session's.

---

## 4. Write perimeter — documents, code, and tool-recorded state

**Documents written — three. Two are the prompt's permitted set; the third is declared here
because a perimeter that hides a write is worse than a perimeter with an extra row:**
1. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md`
   — header block, frontmatter `round`, §1A table rows, new §§3A/4A/5A/6A/7A, §10 heading +
   lead + D9 index row, new §10.4, §11 round 6, new §12A.
2. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/planner/20260824_mechanism_inventory_round_1.md`
   — this file (new; `handoffs/planner/` created to hold it).
3. `docs/archgraph-anchor-observations.md` — one appended entry, **outside the prompt's stated
   perimeter**. It discharges a standing owner brief that predates this prompt and that the
   shaper's round 4 also discharged alongside a narrow perimeter (intention §11 R4-a). The
   entry records zero graph writes and what the three node reads returned. Flagged rather than
   folded, so the coordinator can rule on the perimeter conflict.

**Code: none.** No file under `app/` was modified, created or deleted.
**Tests: none.** No test file touched; the suite was never invoked.
**Architecture graph: zero writes.** Reads only — `archgraph_status` (204 nodes, 308 edges,
valid, 6 stale, 3 pending reviews, permission mode `review`), and three `archgraph_get_node`
calls: `domain-item-economics`, `endpoint-item-economics-task-budget-allocations`,
`decision-money-audience-admin-manager-only`. `archgraph_compute_impact` was **not** called —
no finding indicated a boundary the intention had not already settled.
`.archgraph/contexts/current-task.md` was **not** read or written; it belongs to another task.
The pre-existing `.archgraph/architecture.yml` modification and `.archgraph/backfill/` in
`git status` are not this session's.

**Scratch files** (outside the repo, in the session scratchpad, not part of the perimeter):
`mi_probe.py`, `mi_probe2.py`, and the six `editN.py` scripts that applied the intention edits.

**Nothing was committed.** The tree is left dirty with the two documents above.

---

## 5. The probes, verbatim and re-runnable

Both run from `backend/app/` with `PYTHONPATH=. .venv/bin/python`. Pure domain, no database.

### 5.1 P1–P8 (`mi_probe.py`)

```python
from decimal import Decimal
from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep, divide_production_budget, _budget_seconds, _step_state_is_terminal)
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum as S
from beyo_manager.domain.item_economics.calculator import calculate_consumed_cost_minor

# P1 — the section state is a str; enum-set membership is constantly False
d = divide_production_budget(Decimal("60.00"), [
    DivisionStep("s1", S.COMPLETED, "secA", 1000, 1),
    DivisionStep("s2", S.WORKING,   "secB",  500, 2)])
for r in d["sections"]:
    st = r["state"]
    print(r["working_section_id"], repr(st), type(st).__name__,
          st in TERMINAL_STEP_STATES,
          st in {s.value for s in TERMINAL_STEP_STATES},
          _step_state_is_terminal(r), r["left_seconds"], r["share_state"])

# P2 no steps | P3 all excluded | P4 allowed=None | P5 blocked/paused/pending
print(divide_production_budget(Decimal("10.00"), []))
print(divide_production_budget(Decimal("60.00"), [
    DivisionStep("s1", S.SKIPPED, "secA", 600, 1),
    DivisionStep("s2", S.CANCELLED, "secB", 300, 2)])["sections"])
print(divide_production_budget(None, [DivisionStep("s1", S.WORKING, "secA", 100, 1)]))
print(divide_production_budget(Decimal("60.00"), [
    DivisionStep("s1", S.BLOCKED, "secA", 0, 1),
    DivisionStep("s2", S.PAUSED,  "secB", 0, 2),
    DivisionStep("s3", S.PENDING, "secC", 0, 3)])["sections"])

# P6 — no half-even tie is reachable from a Numeric(12,2) allowance
print([n for n in range(200)
       if abs((Decimal(n)/100*60) - int(Decimal(n)/100*60)) == Decimal("0.5")])
print(_budget_seconds(Decimal("-12.50")), _budget_seconds(Decimal("0.01")))

# P7 — input strictness and the missing sign guard
rate = Decimal("3.7500")
for v in (60, True, 60.0, Decimal(60), -60, 0):
    try: print(v, calculate_consumed_cost_minor(v, rate))
    except Exception as e: print(v, type(e).__name__, e)
for r in (Decimal("3.75"), 3.75, None, 4, Decimal("0.0000")):
    try: print(r, calculate_consumed_cost_minor(60, r))
    except Exception as e: print(r, type(e).__name__, e)

# P8 — int(rate.scaleb(4)) is exact at scale 4
for s in ["3.7500","0.0001","99999999.9999","12.3456","0.9999"]:
    print(s, int(Decimal(s).scaleb(4)))
```

### 5.2 P9–P11 (`mi_probe2.py`)

```python
from decimal import Decimal
from beyo_manager.domain.item_economics.calculator import (
    calculate_production_budget, calculate_allowed_worker_minutes,
    calculate_consumed_cost_minor, calculate_actual_worker_minutes,
    calculate_remaining_worker_minutes)
from beyo_manager.domain.item_economics.budget_division import _budget_seconds

# P9 — a negative production budget is reachable; the D9 finding
budget  = calculate_production_budget(10000, [15000])          # -> -5000
rate    = Decimal("4.0000")
allowed = calculate_allowed_worker_minutes(budget, rate)       # -> -1250.00
sec     = _budget_seconds(allowed)                             # -> -75000
print(budget, allowed, sec,
      max(0, 0 - sec), calculate_consumed_cost_minor(max(0, 0 - sec), rate),
      max(0, 60 - sec))                                        # -> 75000 5000 75060

# P10 — minute domain vs second domain
am = Decimal("60.00")
for a in (3599, 3600, 3601, 3618):
    print(a, max(0, a - _budget_seconds(am)),
          calculate_remaining_worker_minutes(am, calculate_actual_worker_minutes(a)))

# P11 — a non-zero overrun can cost 0
for r in ["3.7500","12.3456","0.9999","41.6667"]:
    rr = Decimal(r)
    print(r, next(s for s in range(1, 2000) if calculate_consumed_cost_minor(s, rr) > 0))
```

Observed: **P9** `-5000 / -1250.00 / -75000 / 75000 / 5000 / 75060`.
**P10** `3599→0 / +0.02`, `3600→0 / 0.00`, `3601→1 / -0.02`, `3618→18 / -0.30`.
**P11** first non-zero cost at `9 / 3 / 31 / 1` seconds respectively.

---

## 6. Notes the planner will need once the gate re-opens

Not contracts — routing information, so the next session does not rediscover it.

- **§9 item 3's "plausibly two phases" survives.** The natural seam is the pure rule
  (`budget_signal.py` + §§3A/4A) versus the service/serializer/route/wire (§§5A/6A/7A + the
  four HC-2a artifacts). Both halves close green independently, and the contract at the seam
  (the rule's signature over section rows and two integers) is stable.
- **Criteria pressure is real.** §§3A–7A register twenty-two contracts against the ledger.
  At ≤ 8 criteria per phase that is more than two phases' worth if every contract earns a row;
  the planner must decide which contracts are discharged by a *shared* row and record the
  reason, rather than splitting into five phases or silently dropping registrations.
- **Rows that cannot fail — the specific ones this project invites.** Named in the contracts
  so the planner can lift them: a `typicals` fixture whose sections carry equal typicals
  (§3A.1); a terminal-predicate fixture with no completed section (§3A.2); a two-call ordering
  test that does not reverse the request order (§7A.2); an `INFEASIBLE` fixture that always
  logs work (§6, D9 permitting); a `no_budget` fixture with no logged time (§5A.2); a
  both-pairs fixture that keeps `over` and `projected_over` mutually exclusive (§6A.2 row 3).
- **The `to_frontend` handoff (§8 must-ship 5) now owes three corrections**, not just the five
  open-question answers: acceptance criterion 2 is unsatisfiable (§4A.3); "N tasks → N rows"
  is per **distinct** id (§7A.1); and two different 422 envelopes exist on the route (§7A.3).
  It must **not** be written into `docs/domains/item_economics/api.md` or that folder's
  `README.md`, which are guarded against naming unregistered item-economics paths (§7A.6).
- **Graph delta remains unrecorded and belongs to the implementing phases** (intention §9 item
  5): one `endpoint` node, one `projection` node under `domain-item-economics`, `reads_from`
  edges mirroring `projection-item-economics-task-budget-allocations`. The graph's 6 stale
  nodes and 3 pending reviews are pre-existing, were left alone, and are observations, not
  gates.

---

## 7. The explicit next gate

**The intention gate — re-opened, and it is the pipeline's strongest.** The order is:

1. **Coordinator relays D9 to the owner verbatim** (charter: re-summarising a card into a
   denser table is how the story dies).
2. **Owner answers D9**, and ratifies the four unilateral resolutions listed above.
3. Whoever folds the answer rewrites the affected sentences — §5.1's `over_seconds`, §6's two
   boundary bullets, D2's "full worked time" sentence, §3.4's `remaining_pot_seconds`, and
   §6A.3 — appends a §11 round 7 entry, and **restores the header to `RATIFIED`**.
4. Only then does the **mechanism-inventory exit gate** pass, and only then may
   **implementation-planner** run.

**May the next actor be implementation-planner? No.** Not until step 3 is done. Until the
header reads `RATIFIED` the coordinator refuses to compile any prompt of any role.

---

## 8. Round-7 addendum — D9 answered and folded (same session, after the owner's ruling)

**This supersedes §7's next-gate sequence.** Steps 1 and 2 of it are done.

### 8.1 The ruling, and why it is better than either branch offered

The card framed the choice as *literal* (a negative pot is an overrun) versus *floored* (a
negative pot is nothing until worked). The owner split it along a different axis — **incurred
versus forecast** — which is the axis the state enum was already built on:

- a negative pot is **known before any work starts**, because the price was set first. That is
  the definition of a forecast, and `projected_over` is the member that carries forecasts;
- an **incurred** overrun requires work. `over` is the member that carries facts, and D2's
  sentence about "the first logged minute" was always describing exactly that.

Branch B would have shipped an untouched, structurally unfunded task as `within_budget` —
silent about a problem the system already knows. Branch A would have shipped it as a red
incurred overrun that never happened. The ruling is the only reading under which every
sentence the owner was originally shown becomes true.

### 8.2 The mechanism, in four lines

```
allowed_seconds_raw    = _budget_seconds(evaluation.allowed_worker_minutes)     # may be negative
over_seconds           = max(0, actual_worked_seconds - max(0, allowed_seconds_raw))   # D9: floors the pot
remaining_pot_seconds  = allowed_seconds_raw - actual_worked_seconds                   # D1: UNCLAMPED, untouched
served allowed_seconds = max(0, allowed_seconds_raw)                                   # D9: keeps client extrapolation exact
```

Plus §6 rank 3 gaining a `remaining_commitment > 0` conjunct — which is **D10**, still open.

**The asymmetry is the contract, not an oversight:** the forecast carries the deficit at full
size (which is what makes "already projected to be overbudget" true rather than asserted), the
incurred figure does not, and the wire carries the floored value because the client extrapolates
`over_seconds` and never the pot.

### 8.3 The transcription risk, named

*"The moment the task transitions to working"* is bound to **`actual_worked_seconds > 0`**, not
to *"a step is in `WORKING`"*. Because the live clock accrues from the instant a step enters
`WORKING`, the two coincide at the moment the owner described and diverge afterwards — a task
worked yesterday and now paused has no `WORKING` step but its overrun is still an incurred
fact, and a state-based reading would drop it back to `projected_over`. Recorded in the
intention at §6A.3 and §11 R7-c, because a paraphrased owner sentence becoming a criterion is a
defect family this project's lineage has already paid for.

### 8.4 What the ruling did NOT touch — so no phase re-litigates it

- **D1 stands.** The projection's second operand is still the unclamped task pot. The single
  most consequential choice this document made needed no revisiting; if anything the ruling
  depends on it.
- **The §1A measurement ledger stands, verbatim.** No entry's text moved. M1's existing wording
  — *"whose unfinished sections' remaining targets exceed its remaining pot"* — already covers
  the new case, since a negative pot is exceeded by any non-negative commitment.
- **D2 stands and is now literally true** for the first time: with the pot floored for the
  incurred figure, an infeasible task's first logged minute makes it `over` by exactly the full
  worked time. Round 5's arithmetic did not deliver that; this does.
- **Every feasible task's verdict is unchanged**, and the 60-second floor still bites exactly
  where D6 put it — verified across eight fixtures (probe P12, intention §12A).

### 8.5 Probe P12

Pure arithmetic over the shipped calculator, `allowed_seconds_raw = -75000` (from P9), rate
`4.0000`, with the D10 guard applied:

| Fixture | `over_seconds` | `projected_over_seconds` | `budget_state` |
|---|---|---|---|
| infeasible, untouched, 3600 s of work ahead | `0` | `78600` | **`projected_over`** |
| the same, once 60 s are logged | `60` | `78600` | **`over`** |
| `allowed == 0` exactly, 3600 s ahead | `0` | `3600` | **`projected_over`** |
| infeasible, untouched, **nothing** left to do | `0` | `75000` served | **`within_budget`** (D10 guard) |
| feasible, untouched, 3600 s ahead, pot 3600 | `0` | `0` | `within_budget` |
| feasible, 1 s past the pot | `1` | `1` | `over` |
| feasible, commitment exceeds pot by 60 s | `0` | `60` | `projected_over` |
| feasible, commitment exceeds pot by 59 s | `0` | `59` | `within_budget` |

### 8.6 New intention deltas this round

§5.1 (`over_seconds` formula), §5.2 (`allowed_seconds` served floored), §6 (both boundary
bullets rewritten, rank 3 conjunct, superseded text preserved in §11 R7-b), §3.3 (the D10
guard and why it was inert until now), §3.4 (D1 explicitly untouched), §3A.4 (arithmetic block
+ two named mutations for the two clamps), §6A.2 (the four infeasible fixtures mapped onto the
seven rows, plus a fourth named mutation), §6A.3 (OPEN → RESOLVED, with the ruling verbatim),
§10 (heading, lead, D9 answered, D10 added), §10.4 (the answer verbatim), **§10.5 (the D10
card)**, **§10.6 (the re-ratification surface — a diff, not a restatement)**, §11 round 7,
§12A (P12), and the header.

**Write perimeter is unchanged from §4** — the same three documents. Still no code, no tests,
no graph writes, no suite run.

### 8.7 The gate, restated

1. ~~Coordinator relays D9~~ — **done; answered.**
2. ~~Owner answers D9~~ — **done; folded.**
3. **Owner answers D10** (§10.5) and confirms the re-ratification surface at intention §10.6,
   which lists every sentence that changed since their round-5 act and nothing else.
4. Header returns to **RATIFIED** with a §11 round 8 entry — **only the owner's explicit act
   writes it.**
5. Then the mechanism-inventory exit gate passes and **implementation-planner** may run.

**May the next actor be implementation-planner? Still no** — one conjunct of the state rule is
open, and the header is not RATIFIED.

---

## 9. Round-8 addendum — D10 answered, and this session correcting itself

### 9.1 The owner's reasoning is sound, and it is verified at the source

*"If all the task steps were skipped before production ran, there is no additive time placed on
the budget, thus no over budget nor projection."* Checked against `divide_production_budget`:
when every step of a task is skipped, every section returns `share_state == "excluded"` with
`left_seconds is None`, so the contributing set is empty and **no time reaches either figure**.
Skipped work is not additive, exactly as stated. The distinction the owner drew — *is there
work still to come?* — is the correct one and is the guard this document now carries.

### 9.2 The card's mechanism was wrong, and only deriving it showed that

D10 branch A was written as **`remaining_commitment > 0`**. Round 7's probe P12 **supplied**
`commitment = 3600` as a fixture parameter instead of taking it from the allocator. Running the
real allocator over seven infeasible shapes gives a different picture:

| Infeasible fixture | contributing sections | `remaining_commitment` | sum-guard | set-guard |
|---|---|---|---|---|
| untouched, one `pending` step | **1** | `0` | `within_budget` **✗** | **`projected_over`** |
| untouched, `working` + `pending` | **2** | `0` | `within_budget` **✗** | **`projected_over`** |
| 60 s logged, work still ahead | 2 | `0` | `over` | `over` |
| **all skipped, never worked** | **0** | `0` | `within_budget` | `within_budget` |
| all skipped, 500 s logged first | 0 | `0` | `over` | `over` |
| all completed, finished | 0 | `0` | `over` | `over` |
| no steps at all | **0** | `0` | `within_budget` | `within_budget` |

`remaining_commitment` is **identically `0` on every infeasible task** — §3.4 cause 2 floors
`distributable_seconds` at `max(0, budget − charged)`, so under a non-positive budget every
section allowance is `0` and every `left_seconds` is `≤ 0`, which the per-section clamp takes to
`0`. The sum guard therefore cannot separate *work ahead* from *nothing left*, and would have
returned `within_budget` for the untouched task with real work ahead — **deleting D9's verdict
one round after the owner made it.**

**Corrected to a contributing-set emptiness test:** `has_work_ahead = any(contributes(s) for s
in sections)`. Every **feasible** verdict is byte-identical under both forms, and the 60/59
floor still bites where D6 put it, so the correction touches infeasible tasks only.

### 9.3 How the defect got in — the lineage's own family, one step upstream

The round-7 probe hand-built a number the production path cannot emit. That is the
row-that-cannot-fail shape moved out of the tests and into **the evidence a contract was
written from**, where no manifest, lint or review checklist was looking. It survived one full
round and was caught only because the owner's question forced a re-derivation.

Two things now guard it: §12A's P12 is a fully derived table with the sum-guard column kept
beside the set-guard column so the two are visibly different; and §3A.4 warns the fixture author
directly — under a negative pot, a section row with positive `left_seconds` is a state the
allocator cannot produce.

### 9.4 One consequence the owner should see before ratifying

`buildOutlook` uses the **sum** form of the guard, so `production-time` shows **no amber on any
infeasible task today**. D9 is therefore new behaviour, chosen deliberately. §2.4's conclusion
that `production-time` could converge onto this rule "with no behaviour change" is qualified in
a new **§2.4A**: converging it would change what that screen renders for infeasible tasks.
Feasible tasks are unaffected. This is in the re-ratification surface as item 5.

### 9.5 New intention deltas this round

§2.4A (new — the convergence caveat), §3.3 (guard replaced, with the measured reason and the
deliberate divergence from `buildOutlook`), §6 rank 3, §3A.4 (set test not sum, a named mutation
for it, and the fixture-author warning), §6A.2 (the worked-example table replaced with derived
figures and a contributing-sections column), §6A.3, §10 (heading, lead, D10 row), §10.5 (the
answer verbatim plus the correction), §10.6 (surface items 4–7 rewritten), §11 round 8
(R8-a…R8-d), §12A (P12 replaced), and the header.

**Write perimeter unchanged from §4** — the same three documents. No code, no tests, no graph
writes, no suite run.

### 9.6 The gate

1. ~~Relay D9~~ — done. 2. ~~Owner answers D9~~ — done, folded. 3. ~~Owner answers D10~~ —
done, folded, and the card's own mechanism corrected. 4. **Owner confirms the re-ratification
surface (intention §10.6) and the header returns to RATIFIED** — only the owner's explicit act
writes it; a §11 round 9 entry records it. 5. Then **implementation-planner** may run.

**May the next actor be implementation-planner? Not until step 4.** Every mechanism now carries
a contract and no decision is open, but the pipeline gate is the header, and the header is not
RATIFIED.
