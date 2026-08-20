# Plan 3 — D9: the frozen blocks freeze whole

```
state: NOT_STARTED
phase: 3
date: 2026-08-20
depends_on: plan 2 APPROVED (the live basis must exist for T13's mutation to discriminate)
```

## 1. Goal

Implement D9: `final.percent_consumed` (E-P) and the worker face's
`result.percent_consumed` (E-B) stop tracking the request-level percent and derive
from the frozen result record's own stored figures (decision N-4) — a frozen block
never carries a ticking field, and moves on **no** event after the freeze.

**NOT in this phase:** no key added or removed anywhere (HC-4); the **live**
`percent_consumed` on the budget block / status payload is untouched (it ticks, D6);
no change to `ItemCostResult`, the analytics worker, or anything persisted (HC-1).
No handoff (phase 4).

## 2. Read first

1. `master_plan.md` §4 (N-4 — the reconstruction formula and its verification
   obligation), §5.
2. Intention §5.3 (the D9 contract), §4.1A B (the two keys, the two sites, the
   manager-face absence), §4.2, §9A T13, §10.3 D9.
3. Source: `division_serializers.py:_serialize_production_time_final` and
   `:serialize_task_production_time` (the E-P feed);
   `serializers.py:_serialize_result` and `:serialize_task_budget_status` (the E-B
   feed); `item_cost_result.py:ItemCostResult` (the stored figures);
   `calculator.py:calculate_percent_consumed` and `:calculate_variance_worker_minutes`
   (the formula and the identity N-4 rests on).

## 3. Files expected to change

- `app/beyo_manager/domain/item_economics/division_serializers.py` — E-P feed:
  `serialize_task_production_time` computes the frozen percent per N-4 and passes it
  to `_serialize_production_time_final` instead of the request-level percent (the
  budget block's `percent_consumed` keeps the request-level value).
- `app/beyo_manager/domain/item_economics/serializers.py` — E-B feed:
  `serialize_task_budget_status` passes the N-4 frozen percent into
  `_serialize_result` instead of `status.percent_consumed`.
- One test file (new or the phase-2 family) for C1–C5.
- Nothing else. If the implementer routes the computation through the service layer
  instead of the serializers, the file set is declared in the handoff and the two
  serializer sites still carry reciprocal comments naming each other (one-copy rule) —
  but the default is the two-site feed above.

## 4. Ordered tasks

1. **Verify N-4's identity before using it** (master plan §5: a comment asserting a
   property inherits the mutation rule). N-4 reconstructs the frozen denominator as
   `allowed ≡ result.actual_worker_minutes + result.variance_worker_minutes`, which
   holds iff `calculate_variance_worker_minutes(allowed, actual) == allowed − actual`.
   Read the calculator definition, compute one worked example by hand in the test
   (C2), and only then wire the sites.
2. The two feed-site changes, each with a comment naming the other site and D9's
   one-line reason (resolvable from a clean checkout — no criterion IDs, no round
   numbers).
3. Tests C1–C5, mutation ledger per master plan §5.

## 5. Acceptance criteria

- **C1 — T13, E-P row.** Fixture: task with a persisted result whose step is re-opened
  into `working` with an open record (live request percent ≠ frozen percent by
  construction). One payload: live fields tick; the whole `final` block —
  `percent_consumed` included — byte-identical to the same task's pre-open payload.
  **Named mutation (call site: `division_serializers.py:serialize_task_production_time`,
  the argument feeding `_serialize_production_time_final`):** feed the request-level
  percent back ⇒ contract = frozen value, mutation = live value, red.
- **C2 — T13, E-B worker-face row, its own fixture and its own mutation** (site:
  `serializers.py:serialize_task_budget_status`, the `percent_consumed=` argument) —
  two sites, two rows, sweep the class. The row's fixture also carries the C2 worked
  example: frozen percent computed by hand from the result's stored
  `actual_worker_minutes` and `variance_worker_minutes`, asserted as an exact literal
  (never an equality between two calls — master plan §5).
- **C3 — re-commit immunity** (N-4's reason): supersede the evaluation and commit a
  new one with a **different** `allowed_worker_minutes`; the frozen percent is
  byte-identical before and after (it derives from the result row alone). This row is
  why N-4 reconstructs the denominator instead of reading the current evaluation.
- **C4 — the manager face still has no `percent_consumed` key in its result block**
  (§4.1A B key-walk row), and the **live** percent on all three surfaces still ticks
  (one row asserting the budget-block percent moved while `final`'s did not — same
  payload as C1).
- **C5 — the no-drift identity.** In the T5 golden state (zero post-freeze drift, same
  evaluation) the new source produces the **same value** as the old wiring — proven by
  the plan-1 golden test staying green with its files untouched (read-only in this
  phase's diff, as in plan 2 C1). This is the criterion that makes D9 invisible to
  every frozen task that has not been reopened.

## 6. Notes

- `_decimal(…)` serialization of the percent must round-trip identically for the
  reconstructed value — if `calculate_percent_consumed` quantizes, the frozen input is
  Decimal-exact (both stored fields are `Numeric(12, 2)`), so no new rounding locus
  appears. If the implementer finds one, that is a STOP-and-report, not a judgment
  call (it would be a new rule-6 mechanism outside the contract).
- The E-P internal dict gains an internal key for the frozen percent — internal to the
  serializer input, not a payload key; HC-4 untouched.

## 7. Review log

(empty — append-only)
