---
plan: plan_5
role: implementer
round: 5
date: 2026-08-24
---

# Plan 5 — fix round 5. Two edits, no production change. **This is the last round.**

The delta re-review returned one blocking and one should-fix. **Both are consequences of the
coordinator's own round-4 prescription, not of your work** — round 4 did exactly what it was asked
and its decoupling is correct and stays.

**Its acceptance is two measurable facts, which the coordinator will verify directly. No further
review is owed after this.**

## Gate check — content only, no SHA

| # | check | expected |
|---|---|---|
| 1 | `git status --porcelain -- app/` from `backend/` | empty |
| 2 | `plans/plan_5.md` header `state:` | `CHANGES_REQUESTED` |
| 3 | master plan §4 row 5 | `CHANGES_REQUESTED` |
| 4 | `planning/intention.md` header `status:` | **`RATIFIED`** |
| 5 | `redis-cli ping` | `PONG` |
| 6 | `grep 'datetime(2026, 10, 30' …/test_narrowed_price_scenario.py` | **a hit** — the typed literal edit 2 removes |

**`HEAD` is deliberately not gated on.** `.archgraph/` is closed under D31.

## Edit 1 — BLOCKING. Add **C1(d)**: the spec branch's clock, guarded directly

**The finding.** `typical_times_statement` has **two independent cutoff lines in duplicated
source**: `get_working_section_typical_times.py:40` on the **spec** branch (every narrowed task)
and `:147` on the no-spec branch. C1(b) used to exercise `:40`. Round 4's move to `plain_task` put
it on `:147` and left `:40` covered by nothing — measured, the whole-suite bite set of a `:40`-only
clock defect is **∅**.

**Do not move C1(b) back.** Its `plain_task` form is right. Add a new row instead.

**C1(d) is written in §6A.** Assert at **statement level**, with no `_typical_block` on the path —
that is what makes it immune to narrowing mutations:

```python
spec = TypicalFilterSpec(item_category_ids=frozenset({category_id}))
inside  = await db_session.execute(typical_times_statement(ws, specs=(spec,), now=FROZEN))
outside = await db_session.execute(typical_times_statement(ws, specs=(spec,), now=FROZEN + timedelta(seconds=1)))
# narrowed_sample_count: 5 inside, 0 outside — exact literals both sides
```

Use `seed_divergent_category_task` and derive `FROZEN` as in edit 2. Place it beside C1 in
`test_narrowed_price_scenario.py` (C1(c) already sets the recorded-deviation precedent).

**Named mutation C1(iii):** `get_working_section_typical_times.py:40` (**definition**, the **spec**
branch's cutoff) — replace the injected-clock expression with `datetime.now(timezone.utc)`,
**leaving `:147` untouched**. **Row (d) alone must redden**, on the sample counts. Probe on that
file is authorized (§4A N3): apply, observe, revert, md5.

## Edit 2 — SHOULD-FIX. Derive C1(b)'s clock; stop typing it

**The finding, measured.** C1(b)'s discriminating power rests on the fixture's `2026-08-01` and
the test's `2026-10-30` being exactly `TYPICAL_WINDOW_DAYS` apart — a hand subtraction referenced
nowhere. With `TYPICAL_WINDOW_DAYS = 91` and C1(i) applied, **`test_c1b` passes**, and the red
lands only on `test_c1a` — the same observable `test_c1a` already asserts. **That is verbatim the
defect round 1's B2 was raised to fix.** The row would go quiet without announcing it.

**Fix:** export the boundary from the fixture module as a named constant and derive the clock.

```python
# _narrowing_fixture.py — name the value the seed already uses
DIVERGENT_BOUNDARY_CLOSED_AT = datetime(2026, 8, 1, tzinfo=timezone.utc)
```
```python
# test_narrowed_price_scenario.py
from beyo_manager.domain.item_economics.typical_constants import TYPICAL_WINDOW_DAYS
frozen = DIVERGENT_BOUNDARY_CLOSED_AT + timedelta(days=TYPICAL_WINDOW_DAYS)
```

**`_narrowing_fixture.py` may be edited for this one purpose only** — naming the constant the seed
already uses, so the seed and the test reference one value. **No seed's behaviour may change.**
`test_c5` and `test_c8` run at `2026-08-24T12:00` and are unaffected either way.

Use the same derived constant for C1(d)'s `FROZEN`.

## Not asked of you

- **N1** — `_typical_block:157`'s `spec_index != 0` guard is uncovered. Correct defence-in-depth,
  no reachable defect today. **Recorded; add no row.**
- **N2** — C2 row (a)'s criterion prose was corrected in the plan; **the test is fine as shipped.**
- **S1 from round 1** — §2B S-7 still has no owner, deliberately. **Do not build a test for it.**

## Ledger

`C1 3 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 · C7 1 · C8 2` = **16** named mutations plus **2** planted
probes = **18 rows**. Print the summands. **Re-run C1(i) and the new C1(iii); cite the rest from
round 4** and say which you cited.

**When you re-run C1(i), state which line reddens in `test_c1b`** — it must remain the
byte-identity assertion, not the numeric one.

## Evidence

**One L4 at the end.** Everything else L1. **No `app/beyo_manager/` change is expected** — if you
find yourself editing production, stop and report.

## Closing

Handoff to `handoffs/implementer/<date>_plan5_fix_round5_handoff.md`: both edits with observed
reds · C1(iii)'s red on row (d) alone · which line reddens in `test_c1b` under C1(i) · the ledger
with summands · perimeter diffed · md5 table · closing stamp with the 21-ID diff.

**Do not push. Never `git add -A`.** Stop and report rather than working around a failed gate.
