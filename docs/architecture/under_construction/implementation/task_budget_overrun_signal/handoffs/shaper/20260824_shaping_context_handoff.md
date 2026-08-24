---
plan: planning (project-level — belongs to no phase)
role: shaper
round: 1-3 (the whole shaping session)
date: 2026-08-24
state: CLOSED — shaping complete, intention at READY_FOR_RATIFICATION
verdict: n/a (shaping produces no verdict)
actor: Claude Opus 5 (1M context), intention-shaper role
---

# Shaping context handoff — task budget overrun signal

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing in this document needs the owner. The one outstanding owner act is **D4,
ratification**, and its surface lives in the intention at **§10.1** — not here.

---

## 0. What this is, and how to use it

The owner asked for the shaping session's research to be written down **so the next
agent does not re-derive it**. This is a reference, not an authority: **the intention is
the authority**, and where this document and the intention disagree, the intention wins
and this file is wrong.

Everything below was verified at source on **2026-08-24** against the tree at `4a7cc69`
plus this session's own untracked additions. Line numbers were **derived, not typed** —
each was re-extracted with `grep`/`sed` after the prose was written, and five wrong ones
were corrected in that pass. They are still line numbers: treat a mismatch as drift, not
as a contradiction, and re-anchor on the symbol.

**Read this instead of re-reading eight files. Read the files when you need to change
them.**

---

## 1. Reading order for the next session

| # | Read | Why | Skip if |
|---|---|---|---|
| 1 | `planning/intention.md` §1, §1A, §10.1 | objective, measurement ledger, ratification surface | never skip |
| 2 | This document §3–§5 | the grounding, already verified | never skip |
| 3 | `planning/intention.md` §3, §4, §6 | the three mechanism contracts mechanism-inventory must deepen | you are only relaying the ratification surface |
| 4 | `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md` | the original request, in the frontend's own words | §2 below summarises what it asks and what changed |
| 5 | `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md` | **the collision** — see §7 | never skip before planning |

**Do not re-read** `budget_division.py`, `calculator.py`, `price_scenario.py`,
`get_task_budget_allocations.py` or `get_task_budget_status.py` for orientation — §3 and
§4 carry what they say. Read them when you are writing code that touches them.

---

## 2. What the frontend asked for, and the four places the answer differs

The handoff is well-written and mostly survives intact. Four deltas, each settled in the
intention — listed so nobody re-litigates them from the handoff's text:

| Handoff says | Shipping | Where |
|---|---|---|
| `over` and `projected_over` mutually exclusive | **both pairs populated**, `budget_state` names the headline | owner S2; intention §5.3 |
| money must agree with "the price-scenario pipeline" | money is the **same call** as budget-status (`calculate_consumed_cost_minor`) — the price-scenario chain is the wrong authority and inverting it is wrong twice | intention §4.2; probe §5.2 |
| "WORKER/SELLER only if free" | **not free** — ADMIN/MANAGER only | intention HC-3 |
| `currency` is a three-member enum | **four members** — wire-only `no_currency` | owner D3; intention §5.1 |

Its five open questions are all answered in the intention: Q1 → §5.3, Q2 → §7.4,
Q3 → §3.3, Q4 → §2.4 (yes, and now cheap, but not scheduled), Q5 → §4.1.

**A `to_frontend` handoff carrying these answers is a must-ship item** (intention §8) and
must be a **new dated document** — never an edit of the 2026-08-23 file.

---

## 3. The verified grounding map

### 3.1 The four sibling read surfaces

| Surface | Service | Shape | Roles |
|---|---|---|---|
| `GET /tasks/budget-allocations` | `services/queries/item_economics/get_task_budget_allocations.py` | batched, cap 50, per-**step** | all four |
| `GET /tasks/{id}/production-time` | `.../get_task_production_time.py` | one task, per-**section** | all four |
| `GET /tasks/{id}/budget-status` | `.../get_task_budget_status.py` (+ `_worker.py`) | one task, money | all four, worker face separate service |
| `GET /tasks/{id}/price-scenario` | `.../get_task_price_scenario.py` | one task, money | ADMIN/MANAGER |

All four call the pure allocator `divide_production_budget`
(`domain/item_economics/budget_division.py:289`).

### 3.2 Anchors worth having (all re-verified)

| Symbol | Location | What it is |
|---|---|---|
| `divide_production_budget` | `budget_division.py:289` | the allocator; returns `{budget_seconds, charged_seconds, distributable_seconds, sections, steps}` |
| `_budget_seconds` | `budget_division.py:69` | `quantize(minutes × 60, HALF_EVEN)`; **can return negative** |
| `group_steps_by_section` | `budget_division.py:107` | worked-seconds sum at `:131` — **includes excluded steps** |
| `_governing_step` | `budget_division.py:180` | prefers a non-terminal step ⇒ section state is terminal only when all steps are |
| distributable clamp | `budget_division.py:328` | `max(0, budget − charged)` — **floors; the task pot does not** |
| `TERMINAL_STEP_STATES` | `domain/task_steps/constants.py:4` | `{completed, skipped, failed, cancelled}` |
| `EXCLUDED_STEP_STATES` |  `budget_division.py:25` | `{skipped, cancelled, failed}` — **note: not `completed`** |
| `calculate_consumed_cost_minor` | `calculator.py:326` | **the money authority.** `Decimal(sec)/60 × rate`, `prec=50`, HALF_EVEN |
| `CALCULATION_VERSION` | `calculator.py:20` | currently `2`; **not bumped** by this project (HC-1) |
| `_BUDGET_STATUSES` | `get_task_budget_allocations.py:48` | `{OK, INFEASIBLE}` — the budget-bearing predicate |
| `EconomicsStatusEnum` | `domain/item_economics/enums.py:15` | twelve members |
| `ItemCurrencyEnum` | `domain/items/enums.py:11` | three members; **persisted enum, do not extend** |
| `load_live_worked_seconds` | `services/queries/item_economics/live_worked_seconds.py` | the shared live basis, one map per request |
| batch route precedence | `routers/api_v1/item_economics.py:347` | fixed paths must precede `/tasks/{...}` |

### 3.3 The single most useful fact

`get_task_budget_allocations` **already computes the section rows this project needs and
throws them away** — it serializes only `division["steps"]` at `:311`. The new service is
largely the existing one with a different tail. That is why this is a small project.

### 3.4 Where currency lives (checked exhaustively)

`item_valuations`, `production_cost_basis_versions`, `cost_model_versions`, and the
`item_cost_evaluations.currency` snapshot that copies them at commit under
`validate_currency_equality`. **There is no workspace-level currency** — `workspaces`
carries `name`, `time_zone`, `created_by_id`, `created_at` and nothing else. A round-1
owner card recommended one anyway; it was fiction, caught only because the owner asked
for the card to be explained.

---

## 4. Facts established, so you need not re-derive them

1. **The frontend's settled-section set is character-for-character `TERMINAL_STEP_STATES`.**
   Verified at `packages/item-economics/src/lib/production-time-view-model.ts:244-249`.
   The rule ports with no translation.
2. **`buildOutlook` already projects past an existing overrun.** Its own test at
   `production-time-view-model.test.ts:241-249` passes a negative remaining pot and
   asserts a projection. So the owner's "populate both" decision matches shipped
   frontend behaviour, and `production-time` can converge later with **no behaviour
   change**.
3. **`price-scenario` uses a different rate from every other surface** — the *live*
   `basis_version.cost_per_worker_minute_minor` (`get_task_price_scenario.py:296`), not
   the evaluation snapshot. Correct for a what-if; wrong for costing a committed task's
   overrun.
4. **`Σ participating left_seconds ≡ allowed − actual` — with two exceptions**, both
   measured (§5.1). This is intention §3.4 and the highest silent-failure risk here.
5. **Route-mirror tripwires:** `_EXPECTED_ROUTES` count is **26**, both assertions at
   `test_phase9_item_economics_route_mirror.py:127-128`; the README row set is asserted
   equal at `:115`. Adding one route ⇒ 27, and the README **must** be edited or the test
   reds.
6. **`_ALL_ROLE_ROUTES` (`test_item_economics_router.py:49`) must NOT gain this route** —
   it is manager-gated.

---

## 5. Probes — verbatim and re-runnable

Both ran against the pure domain, no database. Re-run from `backend/app/` with
`PYTHONPATH=. .venv/bin/python`. **These are shaping evidence, not test coverage** — the
plans still own the criteria that pin these behaviours.

### 5.1 The two-operand divergence (intention §3.4)

```python
from decimal import Decimal
from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep, divide_production_budget, _budget_seconds)
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum as S

def run(name, steps, allowed="60.00"):
    d = divide_production_budget(Decimal(allowed), steps)
    actual = sum(s.total_working_seconds for s in steps if not s.is_deleted)
    task_remaining = d["budget_seconds"] - actual
    sum_left = sum(r["left_seconds"] for r in d["sections"]
                   if r["share_state"] != "excluded")
    print(name, "task_remaining", task_remaining, "sum_left", sum_left,
          "delta", sum_left - task_remaining)

run("A clean", [DivisionStep("s1", S.COMPLETED, "secA", 1000, 1),
                DivisionStep("s2", S.WORKING,   "secB",  500, 2)])
run("B excluded-inside-participating",
    [DivisionStep("s1", S.COMPLETED, "secA", 1000, 1),
     DivisionStep("s2", S.SKIPPED,   "secA",  300, 2),
     DivisionStep("s3", S.WORKING,   "secB",  500, 3)])
run("C wholly-excluded-section",
    [DivisionStep("s1", S.COMPLETED, "secA", 1000, 1),
     DivisionStep("s2", S.SKIPPED,   "secB",  300, 2),
     DivisionStep("s3", S.WORKING,   "secC",  500, 3)])
print("negative pot:", _budget_seconds(Decimal("-12.50")))
run("D infeasible", [DivisionStep("s1", S.WORKING, "a", 300, 1)], allowed="-12.50")
```

Observed: deltas **0, −300, 0, +750**. Two independent causes — excluded steps charged
twice, and the distributable floor. See intention §3.4 for the combined form.

### 5.2 The money identity (intention §4.2)

```python
from decimal import Decimal
from beyo_manager.domain.item_economics.calculator import calculate_consumed_cost_minor
from beyo_manager.domain.item_economics.price_scenario import round_half_even

single = lambda sec, tt: round_half_even(sec * tt, 600_000)
def two_step(sec, tt):
    return round_half_even(round_half_even(sec * 5, 3) * tt, 1_000_000)

a = b = 0
for r in ["3.7500", "12.3456", "0.9999", "41.6667", "7.0001"]:
    rate = Decimal(r); tt = int(rate.scaleb(4))
    for sec in range(0, 4001):
        q5 = calculate_consumed_cost_minor(sec, rate)
        a += single(sec, tt) != q5
        b += two_step(sec, tt) != q5
print("cases 20005 | exact-single mismatches", a, "| two-step mismatches", b)
```

Observed: **24** and **502**. All 24 satisfy `(sec × tt) % 600_000 == 300_000` — exact
half-ties, where `calculate_consumed_cost_minor`'s `prec=50` intermediate has already
fallen off the tie. **Conclusion: call the function; never re-derive the arithmetic.**

---

## 6. What I did NOT do — do not infer these from my silence

- **I never ran the test suite.** No baseline in this project is mine, and nothing here
  may be cited as one. Environment topology and the published baseline live in
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
  §10 — **point at it, do not copy it**, and re-verify before trusting a baseline number.
- **I made no architecture-graph writes.** Graph reads only (`status`, four searches, two
  `get_node`). The phase delta — one endpoint node, one projection node, `reads_from`
  edges mirroring `projection-item-economics-task-budget-allocations` — is unrecorded and
  belongs to the implementing phases. Note `status` reported **6 stale nodes and 3 pending
  reviews** at session start; those are pre-existing, were left alone deliberately, and
  are **observations, never gates**.
- **I did not check whether `budget-signals` collides with any route naming convention**
  beyond the mirror test, nor look at `Application_contracts` for a published contract
  that might need a row.
- **I did not read the worker-time-pressure handoff beyond its summary** (§7).
- **I did not create the `plans/` or `prompts/` folders.** The coordinator establishes
  those when the project starts moving. (`handoffs/shaper/` exists because this document
  is a real row in it — which partially supersedes intention §11 R3-c.)

---

## 7. ⚠ The collision the next planner must resolve first

`docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md`
(dated today, seen by the owner) asks for **two additive fields on
`budget-allocations`**: the step's `state`, and a live per-step remaining share — so a
worker starting a "36m" step knows the task actually has 27 minutes left.

**It is the same overrun problem from the worker's side, and it wants to extend the
endpoint this project's HC-2 forbids touching.** The two are not in conflict on their
merits — one is a manager list verdict, the other a worker step figure — but they are in
conflict on `budget-allocations`, and on who owns "how much is really left".

Do not plan either in isolation. At minimum, decide before phase 1 whether HC-2 survives
contact with the second handoff, because HC-2 is load-bearing for **M6** and relaxing it
after a plan exists is a material semantic change that **re-opens the intention gate**.

---

## 8. This session's full write perimeter

Documents (all new or appended; **no code changed, no tests changed, no graph written**):

1. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md` — new
2. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/shaper/20260824_shaping_context_handoff.md` — new (this file)
3. `docs/archgraph-anchor-observations.md` — one appended entry (owner's standing passive log)

Pre-existing untracked files this session did **not** author and did not modify:
both `from_frontend` handoffs, and `.archgraph/backfill/`.
