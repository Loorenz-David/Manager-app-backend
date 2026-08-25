# Plan 1 — The pure rule: `budget_signal.py`

```
plan: plan_1
project: task_budget_overrun_signal
projection_gate: MANDATORY (rule-6 mechanisms: money call, derivations, the D9/D10 boundary)
```

## 1. Goal

Create the pure domain module `app/beyo_manager/domain/item_economics/budget_signal.py`
(master plan §6.2, the fixed API) that turns the shipped allocator's section rows plus three
task-level operands into a `BudgetSignal`: the incurred and forecast overruns, their costs
**by calling `calculate_consumed_cost_minor`**, the served pot, the four-state verdict, the
four-member wire currency vocabulary and the constructed `no_budget` signal. Unit tests only;
every fixture's section rows come from `divide_production_budget`.

**Explicitly NOT in this phase:** no service, no serializer, no route, no database, no
change to `budget_division.py`, `calculator.py` or any pre-existing file. The `no_budget`
*decision* (budget-bearing ⟺ current committed evaluation) is phase 2's; this phase only
ships the constant row it builds.

## 2. Read first

- Master plan §§5, 6.2, 6.8, 8 (phase-1 graph assessment), 9, 10.
- Intention **header** (confirm `status: **RATIFIED**`, round 10), then §1 HC-1/HC-6, §1A
  (M1–M4 rows and the registration table), **§3, §3A.1–3A.6 in full**, **§4, §4A.1–4A.3 in
  full**, §5.1 (D3), §5.3, **§5A.3**, **§6 and §6A.2–6A.4 in full**, §10 (the decision index
  D1, D2, D6, D8, D9, D10), §12A (P1, **P3**, P7, P8, P11, P12).
- Inventory handoff §1 rows 1, 3, 4, 5, 9, 10, 12, 17, 18 and §6 (the rows that cannot fail).
- Master plan §2 finding **F1** (row 4 unreachable) and **F2** (the two-step mutant's row).
- Code, at source (all source paths below are repository-relative; tests remain relative to
  `backend/app/`): `app/beyo_manager/domain/item_economics/budget_division.py` (`DivisionStep` `:35`,
  `_budget_seconds` `:69`, `_state_value` `:55`, `_governing_step` `:180`,
  `_step_state_is_terminal` `:202`, `divide_production_budget` `:289`, the floor at `:328`);
  `app/beyo_manager/domain/item_economics/calculator.py:83-120` (the guards) and `:326-341`;
  `app/beyo_manager/domain/task_steps/constants.py:4-9`; `app/beyo_manager/domain/task_steps/enums.py:4-12`;
  `app/beyo_manager/domain/item_economics/price_scenario.py:116-124` (the two-step mutant only);
  `app/beyo_manager/domain/items/enums.py:11-14`; `tests/unit/domain/item_economics/test_budget_division.py:1-33`
  (the `selected`/`step` helpers to copy); `tests/unit/domain/item_economics/test_domain_purity.py`
  (the sweep your module must pass — note `FINGERPRINT_TERMS` includes `digest`).

## 3. Dependencies

None (first phase). Gate: intention header `RATIFIED`; projection handoff routed or waiver recorded.

## 4. Files expected to change

| File | Kind |
|---|---|
| `app/beyo_manager/domain/item_economics/budget_signal.py` | NEW |
| `app/tests/unit/domain/item_economics/test_budget_signal.py` | NEW |

No other file. `test_domain_purity.py` sweeps the new module automatically — it is a
pre-existing guard, not a file you touch.

## 5. Ordered tasks

0. **Task 0 — re-derive, then map.** Run §7's probe on your tree with
   `PYTHONPATH=. .venv/bin/python <probe>` and diff its emitted rule figures against the
   corresponding §6 rows. The two figures the probe does not emit have named independent
   derivations: C4(e) is the excluded-allocation shape in intention §12A P3 (the test's local
   `rows(...)` helper must confirm `remaining_commitment == 0` and `has_work_ahead is False`),
   and C5(f)'s three pure conversions are intention §12A P8. A mismatch is a **finding against
   this plan** (Review log), never a number to change in a test. Then write the trace map: every criterion row → the test id that discharges it;
   every test you intend → its row. A test with no row is not written.
1. Write `test_budget_signal.py` **from §6's table**, one test per criterion row or one
   parametrized test per enumerated block; local `selected(...)`/`step(...)` helpers copied
   from `test_budget_division.py:15-33`; a local `rows(allowed, steps, typicals)` helper that
   returns `divide_production_budget(...)` so no test ever hand-builds a section row.
2. Implement `budget_signal.py` exactly as master plan §6.2 fixes it. Imports:
   `TERMINAL_STEP_STATES` (constants), `ItemCurrencyEnum`, `calculate_consumed_cost_minor`,
   `dataclasses`, `decimal.Decimal`, `typing` (`Final`, `Mapping`, `Sequence`). Nothing from
   `budget_division` is *required*; importing `_step_state_is_terminal` is admissible (§3A.2).
3. Run L1 green; then run **every** mutation in §6.1, one at a time, each reverted
   (md5-verify the module after each), recording the failing test id(s) and the assertion line.
4. L2 (master plan §10) for the item-economics radius; then **exactly one** L4 stamp on the
   tree you hand over; ID-diff against the 21-ID baseline.
5. Handoff (`handoffs/implementer/<date>_plan_1_round_1.md`): write perimeter, the mutation
   ledger (§6.1, closed — 34 declared, 34 run), the L4 record, the graph assessment (§8:
   expected "no delta" or one `source_file` node — state which and why), and the owner layer.

## 6. Tests / acceptance criteria

Conventions: rate `Decimal("3.7500")` (`tt = 37500`) unless stated; `allowed = Decimal("60.00")`
(`raw = 3600`) unless stated; typicals **equal** (`A: 1800, B: 1800`) unless stated; section
rows always from `divide_production_budget`. Every figure below was derived by the planner's
probe (§7) on tree `f376928`; re-derive in Task 0.

### C1 — the "still to come" predicate and the eight-member partition · trace **§3.2, §3A.2, §3A.3 → M1**

Fixture: steps `x` (state *s*, section `A`, worked 100) and `y` (`pending`, `B`, worked 0).

| Row | Assertion | Expected |
|---|---|---|
| C1(a) | one sub-row per `TaskStepStateEnum` member as `x`'s state: `contributes(section_A)` | `pending, working, paused, blocked` → **True** (`left_seconds == 1700`, an `int`); `completed` → **False** with `left_seconds == 1700` still an `int`; `skipped, failed, cancelled` → **False** with `left_seconds is None`, `share_state == "excluded"` |
| C1(b) | `has_work_ahead(sections)` on the same eight fixtures | True for the first four; for `completed`/`skipped`/`failed`/`cancelled` still **True** — section `B` (`pending`) contributes. Then the same eight with `y` **removed**: True for the first four, **False** for the last four |
| C1(c) | `_TERMINAL_STATE_VALUES == frozenset(s.value for s in TERMINAL_STEP_STATES)` and every member satisfies `type(m) is str` | True |
| C1(d) | the module's **source text** (`inspect.getsource(budget_signal)`) contains none of the eight `TaskStepStateEnum` values as a quoted literal (`'"pending"'`, `"'pending'"`, … all sixteen spellings) | absent |

### C2 — the per-section clamp is inside the sum · trace **§3.3, §3A.4 → M3**

Fixture P-A: `a` (`working`, `A`, 2400), `b` (`paused`, `B`, 1200). Derived rows:
`A left −600 (over_share)`, `B left 600 (on_track)`; `actual 3600`, pot `0`.

| Row | Assertion | Expected |
|---|---|---|
| C2(a) | `remaining_commitment(sections)` | `600` |
| C2(b) | `compute_budget_signal(...).projected_over_seconds` | `600` (`projected_over_cost_minor == 38`) |
| C2(c) | `.budget_state` | `projected_over` — the signal M3 demands, not silence |

### C3 — the two operands, their clamps, and their types · trace **§3.4 (D1), §6A.3 (D9), §3A.4, §3A.5 → M1, M4**

| Row | Fixture (derived) | Assertion | Expected |
|---|---|---|---|
| C3(a) | P-C: `allowed = Decimal("-12.50")` (`raw −750`), one step (`pending`, `A`, 0) | `over_seconds, projected_over_seconds, allowed_seconds, budget_state` | `0, 750, 0, projected_over` (`projected_over_cost_minor == 47`) |
| C3(b) | P-D: `-12.50`; `a` (`working`, `A`, 60), `b` (`pending`, `B`, 0) | `over_seconds, over_cost_minor, projected_over_seconds, budget_state` | `60, 4, 810, over` — D2 literally true: the first logged minute is `over` by exactly the worked time |
| C3(c) | P-B (D1's required fixture): typicals `A: 1000, B: 2000`; `a1` (`completed`, `A`, 1000), `a2` (`skipped`, `A`, 300), `b` (`working`, `B`, 500). Derived: `A completed, allowance 1100, worked 1300, left −200`; `B working, allowance 2200, worked 500, left 1700`; actual 1800; pot 1800 | `projected_over_seconds, budget_state` | `0, within_budget` (the sum-side alternative would give `200, projected_over`) |
| C3(d) | rows (a)–(c) | every field of `BudgetSignal` except `budget_state` satisfies `type(v) is int` (rejects `bool`, `Decimal`) | True |

### C4 — the floor, the D10 guard, and the allocator's edge shapes · trace **§3.3 (D6, D10), §3A.4, §3A.6 → M1, M3**

| Row | Fixture (derived) | Assertion | Expected |
|---|---|---|---|
| C4(a) | P-G59: `a` (`completed`, `A`, 1859), `b` (`pending`, `B`, 0) | `projected_over_seconds, budget_state` | `59, within_budget` (§6A.2 row 6: served, not signalled) |
| C4(b) | P-G60: `a` (`completed`, `A`, 1860), `b` (`pending`, `B`, 0) | `projected_over_seconds, budget_state` | `60, projected_over` |
| C4(c) | P-E: `-12.50`; `a` (`skipped`, `A`, 0), `b` (`skipped`, `B`, 0) | `has_work_ahead, remaining_commitment, projected_over_seconds, budget_state` | `False, 0, 750, within_budget` |
| C4(d) | P-F: `-12.50`; no steps (`sections == []`) | same four | `False, 0, 750, within_budget` |
| C4(e) | `60.00`; `a` (`skipped`, `A`, 600), `b` (`cancelled`, `B`, 300) (intention P3 shape) | `remaining_commitment, has_work_ahead` | `0, False` |

### C5 — money is a call, and what a call costs · trace **§4.2, §4A.1, §4A.2 (pure transform only), §4A.3, §12A P8 → M2**

Single section `A`, typical 1800 (allowance 3600), one `completed` step with the worked seconds
below; `actual = worked`.

| Row | worked | Assertion | Expected |
|---|---|---|---|
| C5(a) | 3736 | `over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor` | `136, 9, 136, 9` — the exact-rational half-even gives **8** |
| C5(b) | 3752 | same | `152, 9, 152, 9` — the exact-rational gives **10** |
| C5(c) | 3640 | same | `40, 2, 40, 2` — the two-step price-scenario inverse gives **3** (F2) |
| C5(d) | 3608 and 3609 | `over_seconds, over_cost_minor, budget_state` | `8, 0, over` and `9, 1, over` — a red badge naming no money is correct (§4A.3) |
| C5(e) | P-H7 (`a` working 600, `b` pending 0; actual < allowed) | `over_seconds, over_cost_minor` | `0, 0` — and `>= 0` asserted explicitly |
| C5(f) | any budget-bearing fixture, with each stated hand-built `Decimal` | `cost_per_worker_minute_ten_thousandths == int(rate.scaleb(4))` | `37500` for `Decimal("3.7500")`; `1` for `Decimal("0.0001")`; `999999999999` for `Decimal("99999999.9999")`. This proves only the pure conversion; plan 2 C8(c) exclusively proves the ORM-read scale and committed-rate invariant. |
| C5(g) | P-H2 through `compute_budget_signal`, with a recording wrapper around the module-local `calculate_consumed_cost_minor` that asserts each argument's exact type/non-negative seconds **before** delegating to the shipped function | ordered wrapper calls | exactly two calls: `(100, rate)`, then `(1900, rate)`; each seconds argument satisfies `type(seconds) is int` and `seconds >= 0`, each rate satisfies `type(rate) is Decimal`, and the returned signal remains `(100, 6, 1900, 119, over)` |

### C6 — the decision procedure, every reachable row · trace **§6, §6A.2, §5.3, §6A.3 (D2, D8, D9) → M4**

| Row | §6A.2 row | Fixture (derived) | Expected `(over_seconds, over_cost, projected_over_seconds, projected_cost, budget_state)` |
|---|---|---|---|
| C6(a) | 1 | `NO_BUDGET_SIGNAL` | `budget_state == "no_budget"`, all seven ints `== 0`, `type(...) is int` each |
| C6(b) | 2 | P-H2: `a` (`completed`, `A`, 3700), `b` (`pending`, `B`, 0) | `(100, 6, 1900, 119, over)` — **both pairs populated** |
| C6(c) | 3 | P-H3: `a` (`completed`, `A`, 1830), `b` (`paused`, `B`, 1790) | `(20, 1, 30, 2, over)` — projected pair non-zero **below the floor** on an `over` row |
| C6(d) | 5 | P-G60 (as C4(b)) | `(0, 0, 60, 4, projected_over)` |
| C6(e) | 6 | P-H6: `a` (`completed`, `A`, 1830), `b` (`pending`, `B`, 0) | `(0, 0, 30, 2, within_budget)` — the row a plan forgets |
| C6(f) | 7 | P-H7: `a` (`working`, `A`, 600), `b` (`pending`, `B`, 0) | `(0, 0, 0, 0, within_budget)`, `allowed_seconds 3600`, `actual_worked_seconds 600` |
| C6(g) | 2 (competition) | P-D (as C3(b)) | `budget_state == over` although `projected_over_seconds == 810 >= 60` and `has_work_ahead` |
| C6(h) | F1 invariant | P-H4: `a` (`completed`, `A`, 1800), `b` (`completed`, `B`, 1801) plus rows (b), (c), (g) | `over_seconds > 0` ⇒ `projected_over_seconds >= over_seconds`; P-H4 gives `(1, 0, 1, 0, over)` — **row 4 of §6A.2 (over with projection 0) is unreachable** and no test may expect it |

### C7 — the wire currency vocabulary and the sentinel · trace **§5A.3, §5.1 (D3) → M4**

| Row | Assertion | Expected |
|---|---|---|
| C7(a) | `NO_CURRENCY`; `CURRENCY_VOCABULARY` | `type(NO_CURRENCY) is str` and `NO_CURRENCY == "no_currency"`; vocabulary `== frozenset({"swedish_krona", "danish_krona", "euro", NO_CURRENCY})`, every member `type(m) is str` |
| C7(b) | `ItemCurrencyEnum` | exactly three members, none with `.value == NO_CURRENCY` — asserted through a local helper `_assert_persisted_currency_enum_untouched(enum_cls)`; **rule-15 probe row:** the same helper applied to a local four-member `enum.Enum` copy carrying `NO_CURRENCY = "no_currency"` raises `AssertionError` |
| C7(c) | the quoted literal `"no_currency"` (either quote style) occurs **exactly once** across `app/beyo_manager/**/*.py` (rglob from the package root, `.venv` excluded) | `1` |
| C7(d) | the module's source text contains none of the three `ItemCurrencyEnum` values as a quoted literal | absent |

### C8 — fixed public API surface · trace **master plan §6.2, §5A.3, §3.3 (D6) → M1, M4**

| Row | Assertion | Expected |
|---|---|---|
| C8(a) | `BUDGET_STATE_NO_BUDGET`, `BUDGET_STATE_OVER`, `BUDGET_STATE_PROJECTED_OVER`, `BUDGET_STATE_WITHIN_BUDGET`, and `BUDGET_STATES` | exact strings `no_budget`, `over`, `projected_over`, `within_budget`; `BUDGET_STATES == frozenset({the four exact constants})` |
| C8(b) | `PROJECTED_OVER_FLOOR_SECONDS` | `type(...) is int` and `== 60` |
| C8(c) | `tuple(BudgetSignal.__dataclass_fields__)` | exactly `(budget_state, over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor, allowed_seconds, actual_worked_seconds, cost_per_worker_minute_ten_thousandths)` — no `task_id`, no `currency` |
| C8(d) | assign any field on a constructed `BudgetSignal` | raises `FrozenInstanceError`; `BudgetSignal.__dataclass_params__.frozen is True` |
| C8(e) | `inspect.signature` plus `typing.get_type_hints` on the four public callables | `contributes(section: Mapping[str, object]) -> bool`; `remaining_commitment(sections: Sequence[Mapping[str, object]]) -> int`; `has_work_ahead(sections: Sequence[Mapping[str, object]]) -> bool`; and keyword-only `compute_budget_signal(*, sections: Sequence[Mapping[str, object]], allowed_seconds_raw: int, actual_worked_seconds: int, cost_per_worker_minute_minor_snapshot: Decimal) -> BudgetSignal` — exact names, parameter order/kinds, and resolved annotations |

### 6.1 Named mutations — the closed set (35)

Apply one at a time in `budget_signal.py` unless a site is named; revert and md5-verify after each.

| # | Mutation (site) | Must redden |
|---|---|---|
| MUT-01 | `_TERMINAL_STATE_VALUES = TERMINAL_STEP_STATES` (definition) | C1(a) `completed` sub-row, C1(c) |
| MUT-02 | `_TERMINAL_STATE_VALUES = frozenset({"completed","skipped","failed","cancelled"})` (typed out) | C1(d) only — C1(a)/(c) stay green, which is why C1(d) exists |
| MUT-03 | `remaining_commitment`: `max(0, sum(...))` instead of `sum(max(0, ...))` | C2(a), C2(b), C2(c) |
| MUT-04 | `remaining_pot_seconds = max(0, allowed_seconds_raw) - actual_worked_seconds` | C3(a) (`projected 0`, state `within_budget`) |
| MUT-05 | `over_seconds = max(0, actual - allowed_seconds_raw)` (inner clamp dropped) | C3(a) (`over 750`, state `over`) |
| MUT-06 | served `allowed_seconds = allowed_seconds_raw` | C3(a) (`-750`) |
| MUT-07 | `remaining_pot_seconds = sum(left for non-excluded sections)` | C3(c) (`200, projected_over`) |
| MUT-08 | pass `Decimal(over_seconds)` at the **over** `calculate_consumed_cost_minor` call site | C5(g)'s first recorded-call seconds-type assertion |
| MUT-09 | construct the returned `BudgetSignal` with `over_seconds=Decimal(over_seconds)` after both money calls | C3(d)'s returned-field type loop |
| MUT-10 | floor `>= 60` → `> 60` | C4(b) |
| MUT-11 | floor `>= 60` → `>= 0` | C4(a) |
| MUT-12 | delete the `has_work_ahead` conjunct | C4(c), C4(d) |
| MUT-13 | `has_work_ahead` → `remaining_commitment(sections) > 0` | C3(a) (loses `projected_over`) — C4(c)/(d) stay green; record that |
| MUT-14 | drop the outer `max(0, …)` on `over_seconds` | C5(e) (negative seconds and negative cost) |
| MUT-15 | pass `Decimal(projected_over_seconds)` at the **projected** `calculate_consumed_cost_minor` call site | C5(g)'s second recorded-call seconds-type assertion |
| MUT-16 | replace the **over** money call with `round_half_even(seconds * tt, 600_000)` | C5(a), C5(b) |
| MUT-17 | replace the **projected** money call with `round_half_even(seconds * tt, 600_000)` | C5(a), C5(b) projected-cost assertion |
| MUT-18 | temporarily import `round_half_even` from `calculator`, then replace the **over** money call with `round_half_even(round_half_even(over_seconds * 5, 3) * int(rate.scaleb(4)), 1_000_000)` — seconds → whole centiminutes, then centiminutes → whole minor units | C5(c) incurred-cost assertion — and **not** C5(a)/(b); record that |
| MUT-19 | temporarily import `round_half_even` from `calculator`, then replace the **projected** money call with `round_half_even(round_half_even(projected_over_seconds * 5, 3) * int(rate.scaleb(4)), 1_000_000)` — the same two rounding operations | C5(c) projected-cost assertion |
| MUT-20 | `cost_per_worker_minute_ten_thousandths = int(rate * 1000)` | C5(f) |
| MUT-21 | cascade checks `projected_over` before `over` | C6(b), C6(g) |
| MUT-22 | zero the projected pair whenever the state is `over` | C6(b), C6(c), C6(h) |
| MUT-23 | zero the projected pair whenever the floor is not met | C6(c), C6(e) |
| MUT-24 | a second `"no_currency"` literal anywhere in `beyo_manager/` (plant in `budget_signal.py`) | C7(c) |
| MUT-25 | `CURRENCY_VOCABULARY = frozenset({"swedish_krona", "danish_krona", "euro", NO_CURRENCY})` | C7(d) only — C7(a)/(c) stay green |
| MUT-26 | omit `BUDGET_STATE_WITHIN_BUDGET` from `BUDGET_STATES` | C8(a) |
| MUT-27 | `BUDGET_STATE_OVER = "OVER"` | C8(a) |
| MUT-28 | `PROJECTED_OVER_FLOOR_SECONDS = 61` | C8(b) |
| MUT-29 | add `task_id: str = ""` as the final `BudgetSignal` field | C8(c) — remains importable because the new field has a default |
| MUT-30 | change `@dataclass(frozen=True)` to `@dataclass` | C8(d) |
| MUT-31 | add `extra: int = 0` to `contributes` | C8(e)'s `contributes` signature sub-check |
| MUT-32 | change `remaining_commitment` return annotation to `bool` | C8(e)'s `remaining_commitment` annotation sub-check |
| MUT-33 | change `has_work_ahead` parameter annotation to `Sequence[object]` | C8(e)'s `has_work_ahead` annotation sub-check |
| MUT-34 | remove `*` from `compute_budget_signal` | C8(e)'s keyword-only parameter-kind sub-check |
| MUT-35 | `NO_CURRENCY = "wrong_currency"` | C7(a) sentinel-value assertion, C7(c) one-literal assertion |

Rule 12: each mutation is shown to reach **its own** row; a mutation that reddens only an
earlier assertion in the same test is a miss and is recorded as such.

## 7. The probe — re-run in Task 0

Reproduced from the planner's session (scratch `plan_probe.py`, tree `f376928`). Run from
`backend/app/`:

```python
from decimal import Decimal
from beyo_manager.domain.item_economics.budget_division import DivisionStep, divide_production_budget
from beyo_manager.domain.item_economics.typical_filters import SectionTypicalEvidence, SelectedTypical
from beyo_manager.domain.item_economics.typical_constants import TYPICAL_MIN_SAMPLE_SIZE
from beyo_manager.domain.item_economics.calculator import calculate_consumed_cost_minor
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum as S

TERM = frozenset(s.value for s in TERMINAL_STEP_STATES)
def sel(section, value):
    ev = SectionTypicalEvidence(section, None, 0, value, TYPICAL_MIN_SAMPLE_SIZE)
    return SelectedTypical(section, value, "section_wide", ev, True, TYPICAL_MIN_SAMPLE_SIZE)
def contributes(r): return r["left_seconds"] is not None and r["state"] not in TERM
def rule(allowed, steps, typ, rate=Decimal("3.7500")):
    d = divide_production_budget(Decimal(allowed), steps, typ); secs = d["sections"]; raw = d["budget_seconds"]
    actual = sum(s.total_working_seconds for s in steps if not s.is_deleted)
    commitment = sum(max(0, r["left_seconds"]) for r in secs if contributes(r)); ahead = any(contributes(r) for r in secs)
    projected = max(0, commitment - (raw - actual)); over = max(0, actual - max(0, raw))
    state = "over" if over > 0 else ("projected_over" if projected >= 60 and ahead else "within_budget")
    return (over, calculate_consumed_cost_minor(over, rate), projected, calculate_consumed_cost_minor(projected, rate), state,
            [(r["working_section_id"], r["state"], r["allowance_seconds"], r["worked_seconds"], r["left_seconds"], r["share_state"]) for r in secs])
st = lambda cid, state, sec, worked, order: DivisionStep(cid, state, sec, worked, order)
EQ = {"A": sel("A", 1800), "B": sel("B", 1800)}
for name, args in {
  "P-A":   ("60.00",  [st("a",S.WORKING,"A",2400,1), st("b",S.PAUSED,"B",1200,2)], EQ),
  "P-B":   ("60.00",  [st("a1",S.COMPLETED,"A",1000,1), st("a2",S.SKIPPED,"A",300,2), st("b",S.WORKING,"B",500,3)], {"A": sel("A",1000), "B": sel("B",2000)}),
  "P-C":   ("-12.50", [st("a",S.PENDING,"A",0,1)], {"A": sel("A",1800)}),
  "P-D":   ("-12.50", [st("a",S.WORKING,"A",60,1), st("b",S.PENDING,"B",0,2)], EQ),
  "P-E":   ("-12.50", [st("a",S.SKIPPED,"A",0,1), st("b",S.SKIPPED,"B",0,2)], EQ),
  "P-F":   ("-12.50", [], {}),
  "P-G59": ("60.00",  [st("a",S.COMPLETED,"A",1859,1), st("b",S.PENDING,"B",0,2)], EQ),
  "P-G60": ("60.00",  [st("a",S.COMPLETED,"A",1860,1), st("b",S.PENDING,"B",0,2)], EQ),
  "P-H2":  ("60.00",  [st("a",S.COMPLETED,"A",3700,1), st("b",S.PENDING,"B",0,2)], EQ),
  "P-H3":  ("60.00",  [st("a",S.COMPLETED,"A",1830,1), st("b",S.PAUSED,"B",1790,2)], EQ),
  "P-H4":  ("60.00",  [st("a",S.COMPLETED,"A",1800,1), st("b",S.COMPLETED,"B",1801,2)], EQ),
  "P-H6":  ("60.00",  [st("a",S.COMPLETED,"A",1830,1), st("b",S.PENDING,"B",0,2)], EQ),
  "P-H7":  ("60.00",  [st("a",S.WORKING,"A",600,1), st("b",S.PENDING,"B",0,2)], EQ),
  "P-J":   ("60.00",  [st("a",S.COMPLETED,"A",3736,1)], {"A": sel("A",1800)}),
  "P-K":   ("60.00",  [st("a",S.COMPLETED,"A",3608,1)], {"A": sel("A",1800)}),
}.items(): print(name, rule(*args))
for s in S:
    r = divide_production_budget(Decimal("60.00"), [st("x", s, "A", 100, 1), st("y", S.PENDING, "B", 0, 2)], EQ)["sections"][0]
    print(s.value, contributes(r), r["left_seconds"], r["share_state"])
print([(s, calculate_consumed_cost_minor(s, Decimal("3.7500"))) for s in (8, 9, 40, 136, 152)])
```

Planner's observed output (2026-08-24): P-A `(0, 0, 600, 38, projected_over)`; P-B
`(0, 0, 0, 0, within_budget)` with rows `A completed 1100/1300/−200`, `B working 2200/500/1700`;
P-C `(0, 0, 750, 47, projected_over)`; P-D `(60, 4, 810, 51, over)`; P-E and P-F
`(0, 0, 750, 47, within_budget)`; P-G59 `(0, 0, 59, 4, within_budget)`; P-G60
`(0, 0, 60, 4, projected_over)`; P-H2 `(100, 6, 1900, 119, over)`; P-H3 `(20, 1, 30, 2, over)`;
P-H4 `(1, 0, 1, 0, over)`; P-H6 `(0, 0, 30, 2, within_budget)`; P-H7 `(0, 0, 0, 0, within_budget)`;
P-J `(136, 9, 136, 9, over)`; P-K `(8, 0, 8, 0, over)`; states: `pending/working/paused/blocked`
contribute with `left 1700`, `completed` does not with `left 1700`, `skipped/failed/cancelled`
do not with `left None / excluded`; money `[(8,0),(9,1),(40,2),(136,9),(152,9)]`.

## 8. Notes

- **Do not write the words "digest" or "fingerprint"** anywhere in the module — the purity
  guard greps the text (master plan §9 rule 9).
- `compute_budget_signal` takes `allowed_seconds_raw` as an `int` the **caller** obtained from
  `division["budget_seconds"]`. Do not call `_budget_seconds` inside the module — that would be
  a second rounding site (§3A.5), even if it agrees.
- The frozen dataclass has **no** `task_id` and **no** `currency` — facts belong to the service.
- The public API is closed by C7/C8: keep `NO_CURRENCY`, the four state constants, `BUDGET_STATES`, the floor,
  the exact dataclass field surface, frozen immutability, and the four fixed callable signatures
  as importable behavior, not merely implementation details.
- Candidate criteria found while implementing go to the Review log as **candidate criterion**
  with the ledger entry they serve; the coordinator folds or refuses them. No silent tests.

## 9. Review log

*(append-only; implementer and reviewer)*

- 2026-08-24 — coordinator consumed projection round 0 (`AMENDMENTS_REQUIRED`): folded PROJ-01–06 into this plan (split exact-type probes; isolated currency derivation; moved the ORM-read rate proof to plan 2 C8(c); added fixed-API coverage; bounded Task 0 derivations; made Read-first source paths repository-relative). Re-projection required before implementation.
- 2026-08-24 — coordinator consumed projection round 1 (`AMENDMENTS_REQUIRED`): folded PROJ-01–05 into this plan (record both production money call sites and split their mutations; corrected precedence reach; isolated the derived-currency mutation; kept the dataclass mutation importable; closed callable signatures). Re-projection required before implementation.
- 2026-08-24 — coordinator consumed projection round 2 (`AMENDMENTS_REQUIRED`): folded PROJ-01–04 into this plan (added P3 and the price-scenario source to Read-first; completed C5(b)'s tuple; made both two-step mutations transcribable; closed `NO_CURRENCY` with its own mutation). Re-projection required before implementation.
- 2026-08-24 — owner explicitly waived further mandatory projection after round 2. Rounds 0–2 are fully folded above; implementation may proceed under the `PROMPT_READY` tracker gate.
- 2026-08-24 — implementer completed phase 1. Built the pure `budget_signal` rule and its allocator-derived unit suite. The fixed contract was followed without new product judgments: terminal states are derived from `TERMINAL_STEP_STATES`; each section is clamped before commitment summing; the served pot and incurred seconds have separate non-negative clamps; `calculate_consumed_cost_minor` is called exactly twice in production order; the floor is 60 seconds and `over` has precedence; currency vocabulary is derived from `ItemCurrencyEnum` plus the sole `NO_CURRENCY` sentinel; and the frozen eight-field dataclass and four callable signatures remain closed. Task 0 matched every planner probe figure, including the two named independent derivations C4(e) and C5(f). The initial criterion pass exposed a missing explicit C4(e) test; it was added before final evidence and all 35 mutations were rerun against the final tree. MUT-07 first used the wrong textual site and produced a false green; it was re-sited to the specified remaining-pot expression and then reddened C3(c). The complete coverage and mutation ledgers, including observed red assertions, are in the implementer handoff. L1 targeted evidence: `63 passed`; L2 radius: `611 passed`; exact L4 stamp: `21 failed / 2758 passed / 1 skipped`, with an empty failing-ID delta against the documented 21-ID baseline. Ruff check and format check passed. Architecture assessment: no graph delta; the pure module is not yet reachable from a mapped endpoint and no existing anchor semantics changed. Phase 1 tracker advanced to `IMPLEMENTED`; checkpoint and closeout commit identifiers are in the handoff.
- 2026-08-24 — reviewer round 1 `CHANGES_REQUESTED` (Codex). **REV-01 (should-fix):** C4(e)'s allocator-originated excluded-row test does not assert its fixture precondition; clearing `division["sections"]` or changing both excluded steps to `completed` leaves the named test green, so the row is vacuous with respect to the excluded-row shape (plan C4(e), intention §12A P3, charter rules 2/15). **REV-02 (should-fix):** the 35 mutation IDs are present, but the handoff omits the required exact pytest node IDs/assertion lines and overclaims sequential reach for MUT-14 (the seconds assertion stops before either cost assertion; the final `>= 0` assertion is independently unreachable after `== 0`) and MUT-30 (the failed assignment guard stops before the dataclass-metadata assertion), contrary to plan task 3 and charter rule 12. Production semantics, purity, D9/D10, task-pot use, both ordered money calls, sentinel derivation and closed API were verified correct. Review variations proved the correctly sited MUT-07 and C5(g)'s call order; all probes were reverted byte-identically. The one review L4 stamp was `21 failed / 2758 passed / 1 skipped`, additions `∅`, removals `∅`. Graph inspection was read-only and confirmed no phase-1 delta. Technical handoff: `handoffs/reviewer/20260824_plan_1_review_round_1.md`.
- 2026-08-24 — coordinator disposition of review r1 under the owner’s criteria-bound instruction: **no fix cycle.** REV-01 is not a plan-1 failure: C4(e) names the skipped/cancelled P3 fixture and requires only `remaining_commitment == 0` / `has_work_ahead is False`, which the test executes and asserts; exact excluded-row shape is already the owned assertion of C1(a), so duplicating it would add unpurchased test surface. REV-02 does not identify a behavioral or criterion-row failure: MUT-14 and MUT-30 each redden their named row, while its requested sub-assertion separation and retrospective node-level handoff expansion exceed plan §6.1 rule 12. The reviewer’s mutation observations are retained as a process lesson for future plans, not a phase-1 code or evidence obligation. Phase 1 is **APPROVED**; no product semantics, source code, or tests changed in this disposition.
