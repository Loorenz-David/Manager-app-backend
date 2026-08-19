---
project: live_clock_for_working_time_economics
role: coordinator (pre-gate review of the intention)
date: 2026-08-19
status: findings for the mechanism-inventory gate — NOT folded into the intention
author: Claude Opus 5, orchestrator of the item-economics pipelines
---

# Coordinator review of `planning/intention.md` (round 2)

**Why this file exists.** The owner asked for this assessment in conversation while the
`simple_valuation_editor` phase 2 review was running. The session that produced it will be
compacted and the model changed before this project starts, so the findings are recorded
here rather than trusted to context. **Nothing in the intention was edited** — these are
inputs to the mechanism-inventory gate, and the owner decides what folds.

Written by the coordinator of `simple_production_budget_division`,
`inline_valuation_versioning` and `simple_valuation_editor`; several findings depend on
facts from those pipelines that are not visible from this document alone.

---

## Verified correct — do not re-spend the pass

**§4.3's claim is the structural keystone and it holds.** Handing live seconds to
`divide_production_budget` leaves `allowance_seconds` untouched. Checked at the code:
`_section_step_allowances` (`budget_division.py`) reads `total_working_seconds` **only for
completed steps** — `allowances = {step: worked for step in completed}`, then
`residual = section_allowance − Σ completed`, split evenly among open steps **by count**. A
completed step has no open working record, so its M1 figure is identically its settled
column. Allowances cannot move because another step is being worked.

Also verified: **`status` OK↔INFEASIBLE cannot flip on the live basis** (§5.3) —
`get_task_budget_status.py:150` tests `evaluation.allowed_worker_minutes`, the committed
allowance, never worked seconds.

---

## 1. §2.6's "no shared files" became false on 2026-08-19

§2.6 states the valuation editor "adds `get_task_price_scenario.py` / `price_scenario.py` in
the same query family. **No shared files.**" True when written; **false as of that
pipeline's phase 2 implement round the same day.**

Its delegation **D-6** was resolved by having `get_task_price_scenario` **call
`get_task_budget_status`** — the same `_build_evaluated_status` this pipeline makes live.
The import is live in the file at checkpoint `48705b3`.

No semantic damage: the price-scenario endpoint consumes `status`, `item_binding` and the
committed evaluation, none of them worked-derived, and its ratified D5 keeps it
gross-of-progress. But three consequences follow that §2.6 currently denies:

- the perimeters are **not** disjoint — changing `_build_evaluated_status` changes a
  dependency of a shipped endpoint;
- the price-scenario integration suite will exercise a live code path, so any assertion in it
  that transitively depends on budget-status-derived numbers becomes time-dependent;
- "merge-order concern, not a semantic one" understates the coupling the planner must scope.

**Same paragraph, second slip:** the claimed router / route-mirror overlap cites **§5.4**,
which is the frontend-handoff obligation, not a router change. HC-4 adds no route and no
field, so this pipeline touches neither the router nor the mirror tests at all.

## 2. Two promises to the frontend that the mechanism contradicts

§6 asserts a step's live figure is **non-decreasing** between reads with no transitions, and
§5.4 promises the frontend that `worked_seconds` decreases "only in the ≤ 1s rounding sense
… **never structurally**."

Both are false in a case §3.1 already handles correctly: **marking an open record's time
wrong.** §3.1 credits 0 for a marked-wrong record, so the instant a manager sets
`recorded_time_marked_wrong` on a *running* record the live figure drops by the whole accrued
share — no state transition involved. Deleting the record or the step does the same.

This is not cosmetic: the frontend is building smoothing on that promise. A client adding
elapsed-since-receipt to a monotonically-growing number, then receiving a value 25 minutes
lower, either snaps backwards or clamps. Either define the case in §6 and carry it into the
§5.4 handoff, or the closeout ships a guarantee the backend does not keep.

## 3. The window rule is under-specified for the multi-open case

§3.1 defines `W_start` **per open record** (`entered_at − 1 day`); §3.4 says one sweep **per
distinct credited user**. A worker holding two open batch records with different `entered_at`
has two candidate windows and one call. It must be `min(entered_at) − 1 day`; the document
never says so, and choosing the later anchor silently truncates the earlier record's early
segments — §3.2 case 4 reintroduced through the window instead of the divisor.

§11 already nominates the buffer's *sufficiency* for the inventory. Its **anchor** is a
second question and is not on that list.

## 4. E-B's SQL aggregate must be dismantled, and the document doesn't say so

`_build_evaluated_status` computes `actual_seconds` as a **SQL aggregate**
(`func.sum(TaskStep.total_working_seconds)` over the task's non-deleted steps). Going live
means that query cannot produce the number at all — it becomes a per-step fold over the
loader's output. §4.1's "one shared loader … consumed by `_build_evaluated_status`" is right,
but deleting a SQL aggregate from a hot read path is a concrete structural consequence worth
naming before an implementer meets it mid-round.

## 5. T5 is not writable as stated

*"Golden-file comparison of all three payloads … **before/after** the feature."* After the
change lands there is no "before" unless goldens were captured first. The plan must carry the
sequencing explicitly: capture and commit goldens at the pre-change checkpoint, assert against
them afterwards. Otherwise the implementer writes a test comparing the new payload to itself,
which passes vacuously — the exact class of inert check the `simple_valuation_editor` pipeline
caught **four** times.

## 6. E-A's cost is proportional to something unbounded

§3.4's "proportional to *current activity*, never to record accumulation" is true, but
`budget-allocations` accepts up to 50 tasks and nothing bounds the number of **distinct active
workers** across them. T8 asserts one sweep per worker; nothing bounds the workers. Twenty
active workers is twenty sweeps plus the open-record probe, on a batch endpoint. State a
ceiling or a measured worst case.

---

## One process note for whoever runs the gate

§11 closes by nominating the §3.3 bound, the §3.1 window and T8 as "most worth attacking."
**In the neighbouring project that self-assessment pointed away from the weakness three times
running** — the mechanism-inventory, the projection and the first review each found their
defects in the section nobody had flagged, while every nominated claim survived.

Sweep **§6 and §2.6 at equal depth** to §3.3. Finding 2 above is in §6, which nothing
nominated.
