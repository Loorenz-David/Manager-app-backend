---
plan: phase 3
role: review
round: 2
verdict: CHANGES_REQUESTED
date: 2026-08-12
actor: Claude (plan-reviewer)
---

# Phase 3 reviewer handoff — canonical calculator (re-review r2, delta-scoped)

**Verdict: CHANGES_REQUESTED** — 1 blocking, 2 should-fix, 4 notes, 2 lessons.

**All six r1 findings are genuinely closed**, and two of them verified harder than
declared. The fix cycle did its job on everything that was routed. What holds the
gate is a consequence of the *new* contract the fix implemented: R9-1 says
`rederive` never raises a `ValidationError`, and on corrupt snapshots it still does —
including one path this fix's own refactor opened. Plus one of the three rows added
to C9 does not bite. Both are small, and the correction for each is verified below.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — How far does "re-derivation never fails the read" reach?

**Question.** Should `rederive` also survive a *malformed* stored evaluation, or only
one whose numbers disagree?

**Story.** You asked for this in the last round: when an old evaluation no longer
adds up, the page should still render and the mismatch should page an engineer, not
blame the manager reading it. That now works for disagreeing numbers. But if a row is
malformed rather than merely wrong — a term snapshot missing its percentage, or a
rate snapshot stored as 0 — the audit function still throws a validation error and the
manager gets a red box on a page they were only reading. Same lived outcome you
rejected, different door.

**Branches.** *Cover every malformed input too* — one door: any bad row returns the
integrity marker, the read always renders. *Cover only value disagreement* — malformed
rows keep failing loudly, and phases 7–8 must catch that separately.

**Recommendation.** Cover every malformed input — the whole point of an audit function
is that corrupt data is its input, not its crash.

**On silence.** The gate holds; the fix's scope stays undecided and phase 3 cannot
approve.

**Trace.** Finding B3; intention §6A.11 (round 9, R9-1); `calculator.py:439-465`.

## Step 1 — verified perimeter: PASS

`git show 8378a1b` contains **exactly** the four allowed files and nothing else:
`calculator.py`, `test_calculator.py`, the master-plan tracker row, the plan's Review
log. Declared hashes match byte-for-byte — calculator
`1c9a75fa24b0c60da2c6c449b931cac3bafdf8f3a91c288d6cd2e42fffeb5d20`, tests
`971232312acce140aaba6f554ac8c855b16aaf01cabb6f702844f3fe7acc885b`. Working tree
clean at review start and end.

## Step 2 — delta probes

**R2-P1 (B1) — PASS, verified structurally.** Rather than trust the C9 row, I swept
**every** public callable under `getcontext().prec = 6, rounding = ROUND_CEILING` and
compared to baseline: all twelve are byte-identical, including the two that diverged
in r1 — `calculate_remaining_worker_minutes` and `calculate_variance_worker_minutes`
now both return `99999.67` (r1: `99999.7`). Reading confirms it: no public function
performs Decimal arithmetic outside a `localcontext()`; `calculate_production_budget`
and `calculate_variance_cost_minor` are pure `int`, `rederive` and
`validate_currency_equality` only compare. Mutation: removing
`calculate_remaining_worker_minutes`'s wrapper reddens the C9 row (1 failed / 58
passed).

**R2-P2 (B2) — PASS.** The new row is
`test_system_supplied_money_none_is_a_type_error`, driving
`calculate_variance_cost_minor(None, 100)` — a genuinely system-supplied parameter
(`production_budget_minor` carries no `required_identity`), and the assertion names
that parameter in its match string (P-M extension satisfied). The inferred-zero
mutation that left **54/54 green in r1** now reddens exactly this row (1 failed / 58
passed).

**R2-P3 (S2 carrier) — PASS.** Zero occurrences of `ITEM_COST_SNAPSHOT_MISMATCH`
anywhere under `app/`; the only remaining `raise ValidationError` sites in
`calculator.py` are the pre-existing identity guards (term shape, rate underflow,
currency). `rederive` returns `{"marker": REDERIVE_MISMATCH, "mismatches": [...]}`
with `field` / `rederived_value` / `stored_value` entries per §6A.11 round 9. The C7
fixture asserts the marker **and** the exact payload; its two-term fixture is a good
one — the budget correctly does *not* appear as a mismatch, because it is re-derived
from the re-derived amounts rather than the stored ones. (But see S5: three of the
four field branches have no row.)

**R2-P4 (S1) — PASS.** The `or` is gone; each row asserts `valuation.value`,
`basis.value` and `model.value` separately plus the failing-pair label. Re-running the
message-weakening mutation reddens **2 of 3** rows — the P-O bar. For the record, row 2
(`SEK, EUR, SEK`) is structurally immune to that particular mutation: with the
right-hand values stripped, its surviving text still contains both `swedish_krona`
(from `valuation=`) and `euro` (from `basis=`). Not a defect — noting it so a future
round does not re-file it.

**R2-P5 (absorbed guards + S3 + `__all__`) — PASS, with two notes.**
- All three R9-2 rows exist and each bites on its own branch, probed separately on the
  disposable worktree: deleting the negative-percent branch reddens only
  `test_negative_percentage_term_value_is_a_shape_error`; the negative-fixed branch
  only `test_negative_fixed_term_value_is_a_shape_error`; the zero-rate guard only
  `test_zero_rate_reaching_allowance_is_rate_underflow`. One row, one guard, no
  collateral.
- S3: both tokens are live against the module docstring — stripping `renames`
  (never-bump) reddens it, and so does stripping `term formula` (bump). Closed as
  routed. See N9 for what is still unheld.
- `__all__`: every name resolves; nothing defined-here is public except
  `ROUND_HALF_EVEN`, correctly excluded per the §6.5 registry decision; dropping a
  name from `__all__` reddens the new surface row. **It holds 19 names, not 20** — see
  N8.

**Suite — PASS.** `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app`:
**1743 passed / 23 failed / 1 deselected** in 57s. Exactly +5 over r1's 1738 (the five
new tests: system-`None`, three absorbed guards, public surface). Zero connectivity
noise. The 23 failure IDs `diff` **empty** against the phase-1 routed list — N14's
Shopify flake did not fire. Focused suite 59 passed. `ruff check` on both files: clean.

**Archgraph (closing protocol step 2) — unchanged, read-only.** `archgraph_status`
only: revision `671fd92a560fbaffda67e74f21eff8128c55cacfae807d98ab27fdf6e586319b`,
126 nodes / 161 edges, **1 pending item** (the held `domain-item-economics` node),
zero diagnostics, zero stale nodes. **Zero delta from the fix**, exactly as the fix
handoff declares. Nothing promoted, rejected, edited, deprecated or removed. Card 3
still stands: re-anchor to `1–26` / `137–219` / `371–426`-equivalent spans after the
final fix and adjudicate once — note the line numbers have already moved again in this
checkpoint, which is why holding was right.

## Findings

### Blocking

**B3 — `rederive` still raises user-facing `ValidationError`s on corrupt snapshots,
contravening R9-1.** Authority: intention **§6A.11 as amended round 9 (R9-1)** — a
re-derivation disagreement "**never raises a `ValidationError`** and no user-facing
error identity exists for it … calling services log/escalate the marker at error level
and **the read still renders**." Verified live on unsaved ORM instances, three classes:

- **(a) stored `cost_per_worker_minute_minor_snapshot = 0` → `ITEM_COST_RATE_UNDERFLOW`.**
  This is squarely a stored-value-disagrees case (stored `0` vs re-derived `400.0000`)
  and it sits on *this fix's own seam*: the S2 refactor replaced the early raise at the
  rate-mismatch site with an appended mismatch entry, so execution now continues to
  `allowed = calculate_allowed_worker_minutes(budget, stored_rate)`
  (`calculator.py:465`) and dies there instead of returning the marker it just built.
  The column is `Numeric(12, 4) NOT NULL` with **no CHECK > 0**
  (`migrations/versions/90cdd23a828e_item_economics_schema.py:204`), so the row is
  representable — and a zeroed snapshot rate is precisely the integrity event
  `rederive` exists to detect.
- **(b) a corrupt snapshot term shape → `ITEM_COST_TERM_SHAPE_INVALID`** (e.g. a
  percentage term whose `percent_value` is NULL), raised out of
  `calculate_term_amounts` at `calculator.py:439`.
- **(c) a purchase term with NULL `purchase_cost_minor` → `ITEM_COST_PURCHASE_COST_REQUIRED`.**

(b) and (c) are pre-existing — they are in scope only because R9-1 is new, and they are
reported under the charter's passing-glance clause. **Correction:** no path out of
`rederive` may be a `ValidationError`; fold these into the `REDERIVE_MISMATCH` payload
(or a sibling integrity marker), with one criterion row per class and a named mutation
each. **The scope boundary — all malformed inputs, or only value disagreement — is
owner card 1**; if the owner takes the narrow reading, only (a) is blocking and (b)/(c)
become should-fix.

### Should-fix

**S4 — the `calculate_percent_consumed` row added to C9 is decoration.** Proven by
mutation: removing `calculate_percent_consumed`'s `localcontext()` wrapper leaves
**59/59 green**. Its fixture `(Decimal("995.02"), Decimal("203.02"))` is too small for
`prec=6` to change the 2-dp result, so the row cannot hold the wrapper it was added to
guard. Its two siblings are fine — removing `calculate_remaining_worker_minutes`'s
wrapper *does* redden the row. Authority: charter rule 11 / P-N (a safety test that
survives the defect it exists to prevent is decoration); plan C9 as amended.
**Correction, verified end-to-end:** swap the fixture in **both** C9 tuples to
`calculate_percent_consumed(Decimal("0.01"), Decimal("100000.00"))` — with the wrapper
intact 59 pass; with the wrapper removed the row reddens (`InvalidOperation` at
`prec=6`, the same mechanism that makes C9(b)'s Q3 row work).

**S5 — three of the four `REDERIVE_MISMATCH` field branches have no test.** Only
`term[<name>].amount_minor` is asserted. I exercised all four: `production_budget_minor`,
`allowed_worker_minutes` and `cost_per_worker_minute_minor_snapshot` each produce
well-formed entries, so **the code is right** — the contract simply has no arbiter, on
a payload shape introduced this round. Also unpinned: a rate mismatch **cascades** into
a second entry (verified fields
`['cost_per_worker_minute_minor_snapshot', 'allowed_worker_minutes']`), because the
allowance is re-derived from the stored rate. That is defensible but nobody decided it.
Authority: charter rule 2 (enumerate, never sample); §6A.11 R9-1 ("naming the
disagreeing fields"). **Correction:** one row per field branch asserting its exact
payload, plus a row pinning the cascade.

### Notes

- **N8** — `__all__` holds **19** names, not the "20" asserted in the fix handoff, the
  tracker note and probe R2-P5. §6.5's enumerated surface is the 16 registered names +
  `EvaluationSnapshot` + `TermSnapshot` + `REDERIVE_MISMATCH` — `REDERIVE_SKIPPED` is
  already among the 16, so the registry prose double-counts it. **The code is right and
  knowingly so** (the fix log records the dedup explicitly). Only the prose count is
  wrong — a direct repeat of **P-L** ("registries list items, never counts; a criterion
  stating a count derives it from its own table or omits it"). A reviewer taking "20"
  at face value would file a false finding against correct code. → coordinator: correct
  the count in §6.5-adjacent prose and the tracker.
- **N9** — the `CALCULATION_VERSION` constant's own docstring, which **plan task 6**
  names as the contract carrier ("`CALCULATION_VERSION = 1` with §6A.10's
  bump/never-bump contract as its docstring"), has no arbiter: gutting it to
  `"""Version constant."""` leaves 59/59 green, because the test reads the *module*
  docstring — as R2-P5 directed, so the implementer complied. Two docstrings now carry
  the same two lists and can drift apart. → next touch.
- **N10** — `calculate_variance_worker_minutes` (`calculator.py:357-359`) opens a
  `localcontext()` around a call that already opens one; removing the outer wrapper
  changes nothing (59/59). Harmless redundancy, mildly misleading. → next touch.
- **N11** — cosmetic indentation artifact introduced at `calculator.py:390`: the
  f-string inside `validate_currency_equality`'s list comprehension gained four spaces
  for no reason. ruff-clean, zero behavioural effect. → next touch.
- r1's optional **N1** (duplicate test), **N5** (dead `required=False`) and **N6**
  (collection-time fixtures) were correctly not taken — they were optional and the fix
  cycle stayed inside its perimeter.

## Lessons for the plans

- **L5** — R9-1 specified the *happy* mismatch path (values disagree) but not what
  `rederive` does when the snapshot is **malformed** rather than merely wrong. A "never
  raises" contract must enumerate the input classes it covers, or the implementer
  closes only the class the finding named. (Earned: B3.)
- **L6** — when a fix **extends** a hostile-context criterion to new functions, each
  added row needs a fixture chosen so the mutation *bites*, and the fix's mutation
  declaration must name the row it reddens **per function**. One blanket
  "hostile-context row red" hid an inert row among two live ones. Extends **P-I**
  (coverage-fix rows are mutation-tested by the fixer) to say: per row, not per test.
  (Earned: S4.)

## Carry-forward dispositions

Not applicable — CHANGES_REQUESTED, so nothing is carried past an approval. Routing
intent: B3 → fix cycle r3 (scope per card 1); S4, S5 → same cycle; N8 → coordinator
prose correction (§6.5 + tracker); N9, N10, N11 → next touch of these files; L5 → the
intention (§6A.11 input-class enumeration); L6 → master plan §9 beside P-I. r1's
carry-forwards are unchanged: N7 → phase 4/5 wiring arbiter; card 3 graph node still
held.

## Mutation-probe declaration

All probing was done in a **disposable git worktree** at `8378a1b`
(`git worktree add --detach`), never in the main tree.

- `app/beyo_manager/domain/item_economics/calculator.py` — 15 mutations applied and
  reverted (R2-P1 wrapper removal; R2-P2 inferred zero; R2-P4 message weakening; three
  absorbed-guard branch deletions; two module-docstring token strips; the constant
  docstring gutting; an `__all__` name drop; `calculate_percent_consumed` and
  `calculate_variance_worker_minutes` wrapper removals; plus repeat isolation runs).
  Final sha256 `1c9a75fa24b0c60da2c6c449b931cac3bafdf8f3a91c288d6cd2e42fffeb5d20` ✓
- `app/tests/unit/domain/item_economics/test_calculator.py` — 1 mutation (the S4
  counterfactual: C9's `calculate_percent_consumed` fixture swapped in both tuples).
  Final sha256 `971232312acce140aaba6f554ac8c855b16aaf01cabb6f702844f3fe7acc885b` ✓
- `__pycache__` cleared between every probe so no run could read a stale module.
- One non-source file created inside the worktree only: `app/.env`, copied from the
  main tree because it is gitignored and `conftest.py` cannot import settings without
  it. It went away with the worktree.
- Worktree removed (`git worktree remove --force`); `git worktree list` shows only the
  main tree. Main tree verified clean, both hashes unchanged.
- **Database/state side effects: none.** Every probe ran the pure unit module; no
  migrations, no DDL, no writes. The configured development database was never written
  to and remains at head. **Architecture graph: read-only** (`archgraph_status` only);
  revision unchanged.

## Full write perimeter

- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md`
  — appended the reviewer r2 Review log entry (append-only; r1 and fix-r2 entries
  untouched).
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  — phase-3 tracker row only: state `IMPLEMENTED` → `CHANGES_REQUESTED`, actor extended
  to `Codex; reviewer r1 (Claude); Codex (fix r2); reviewer r2 (Claude)`, verdict
  summary appended. All prior actor stamps and every other row preserved verbatim.
- This handoff file.
- **No production or test code was modified.** All probe edits were made in the
  disposable worktree and reverted there before it was removed.
