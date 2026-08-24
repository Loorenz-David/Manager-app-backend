---
plan: plan_5
role: reviewer
round: 2
date: 2026-08-24
---

# Plan 5 — delta re-review. Three questions.

**Model: Opus 5.** This is a **delta** re-review, not a second full pass. Your round-1 review was
consumed in full and every finding is closed; two fix rounds since then touched **one test file**
and **zero production lines**.

**Answer three questions and stop.** If they all hold, say `APPROVED` plainly.

## Gate check — content only

| # | check | expected |
|---|---|---|
| 1 | `git status --porcelain -- app/` from `backend/` | empty |
| 2 | `plans/plan_5.md` header `state:` | `IMPLEMENTED` |
| 3 | master plan §4 row 5 | `IMPLEMENTED` |
| 4 | `planning/intention.md` header `status:` | **`RATIFIED`** |
| 5 | `redis-cli ping` | `PONG` |
| 6 | `grep plain_task …/test_narrowed_price_scenario.py` inside `test_c1b_…` | a hit — round 4's work is present |

**No SHA is gated on, deliberately.** `.archgraph/` is closed under D31 — do not read it for state.

## What changed since your review, and nothing else did

- **B1** → `§6A C8(c)`: C8 drives `get_task_price_scenario` **end to end** and asserts the served
  payload. The mutation that left the whole repository green now reddens it.
- **B2** → C1(b) is DB-backed with the prescribed `FakeDatetime`, then re-pointed at **`plain_task`**
  so a narrowing defect no longer reddens the clock row, with byte-identity asserted **first**.
- **S1** → restated, not tested. §2B S-7's SQL scoping has **no wire observable and no row owns
  it**, recorded as the correct outcome.
- **N1, N4** fixed in test. **N2, N3, N5** declared, not covered.

**Measured by the coordinator, reverted and md5-restored — consume by citation, do not re-run:**

| probe | result |
|---|---|
| C1(i) | `test_c1b` fails at `:127`, the **byte-identity** assertion. Bite: C1(a) + C1(b) |
| C8(ii) — `None` at the service call site | **`test_c8` alone** |
| C8(i) — `specs = ()` at the derivation line | `test_c2d` · `test_c5` · `test_c8` |

Stamp **2707 / 21 / 1**, 21-ID set ∅/∅, tree clean.

## The three questions

**Q1 — Does C1(b) still *compose* clock and window?** It now runs on `plain_task` and asserts
`375` in / `0` out. Is it genuinely proving that the injected clock drives the 90-day cutoff, or
has decoupling reduced it to a test that merely notices a number changed? The fixture pins **all**
completed history at one instant (`2026-08-01`), exactly 90 days before frozen `ctx.now`.

**Q2 — Did moving C1(b) off `narrowed_task` remove coverage nothing else has?** It used to assert
`600` on the narrowed task. Is any property now unobserved that was observed before?

**Q3 — One free pass for a row that cannot fail.** This phase has produced **six**, and **two were
inside rows rewritten to close a previous one**. That is the pattern here, not the exception. The
instrument to distrust by name: `_TypicalSession` discards the statement, so a row built on it
cannot observe anything the SQL decides.

## Scope fence

**Do not re-verify** the perimeter, the stamp, the citation discipline, the orphan sweep, §6D
compliance, the production code, or the graph. Your round-1 review established them and nothing
since has touched them. **Do not re-derive the bite sets above.**

If you find something outside these three questions that is genuinely blocking, report it — but
say explicitly that it is out of the delta's scope so the coordinator can weigh it against the
phase closing.

## Reporting

`APPROVED` or `CHANGES_REQUESTED`, findings ranked, with an owner-readable opening. Handoff to
`handoffs/reviewer/<date>_plan5_rereview_delta_handoff.md`. State **where your evidence ends**.

**No `app/` writes. Do not push. Never `git add -A`.** Findings route through the coordinator —
do not edit the plan.
