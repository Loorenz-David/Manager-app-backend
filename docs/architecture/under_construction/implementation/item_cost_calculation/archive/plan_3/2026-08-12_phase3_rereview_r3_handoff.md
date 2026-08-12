---
plan: phase 3
role: review
round: 3
verdict: CHANGES_REQUESTED
date: 2026-08-12
actor: Claude (plan-reviewer)
---

# Phase 3 reviewer handoff — canonical calculator (re-review r3, delta-scoped: B3/S4/S5)

**Verdict: CHANGES_REQUESTED** — 0 blocking, 1 should-fix, 5 notes, 2 lessons.

**B3 is closed and closed well** — I could not break it. Beyond the three enumerated
R10-1 classes I threw 17 further hostile inputs at `rederive` and every one came back
as the integrity marker; no `ValidationError` escapes on any path. **S4 is closed**
(r2's counterfactual is now the shipped fixture, and it bites). What holds the gate is
one row in **S5**: the owner's pinned rate→allowance cascade has no live arbiter —
deleting the clause that implements it leaves all 65 tests green. The code is correct;
one fixture is not. The verified two-line correction is below, so the next cycle is
small.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. R10-1 answered the only open question and the implementation honours it; card 3
(graph node held) is unchanged and needs nothing until approval.

## Step 1 — verified perimeter: PASS

`git show 8908619` contains **exactly** the five expected files: `calculator.py`,
`test_calculator.py`, the fix handoff, the plan's Review log, the master-plan tracker
row. Declared hashes match byte-for-byte — calculator
`e5f42531d59c66a06e384f772f41c0971d63fa5990189f39276ff6d1d9611a49`, tests
`d7251cdeed549a1ac663253f969a994e8cce1a428815afbeeddab0690497ba30`. Working tree clean
at review start and end. The handoff-committed-inside-the-checkpoint slip was
pre-recorded by the coordinator and is **not** re-filed; the hash is verified from git
directly.

## Step 2 — delta probes

**R3-P1 (B3 totality) — PASS, and totality adversarially confirmed.** All three R10-1
input classes return the `REDERIVE_MISMATCH` payload on unsaved ORM instances:

| Class | Input | Result |
|---|---|---|
| (ii) | NULL typed term value (percentage term, `percent_value = None`) | marker, `term_snapshot` |
| (ii) | duplicate `item_purchase_cost` rows | marker, `term_snapshot` |
| (iii) | zeroed stored rate | marker, `cost_per_worker_minute_minor_snapshot` + cascaded `allowed_worker_minutes` carrying the converted `ITEM_COST_RATE_UNDERFLOW` |
| (iii) | NULL `purchase_cost_minor` + purchase term | marker, `term_snapshot` |
| (i) | value disagreement (budget) | marker, `production_budget_minor` |

Then, as instructed, I went hunting for a **fourth escape route** across 17 further
hostile inputs: negative stored rate; `Decimal("NaN")` as the stored rate; `NaN` as the
stored allowance; `monthly_paid_hours_snapshot = 0` and
`planning_utilization_percent_snapshot = 0` (both division-by-zero); a fixed cost small
enough to trip Q2 underflow; a `float` stored rate; `None` and `str` expected price;
`None` budget; `None` allowance; `None` term `amount_minor`; a `str`
`calculation_type`; a `float` `percent_value`; a negative percent term; empty
`term_rows`; `None` calculation version; and version 2. **Every one returned the marker
(or `REDERIVE_SKIPPED` for version 2). Zero `ValidationError` escapes.** The one
exception found is `term_row.name` — see N12, which is not an R10-1 violation and is
unreachable for real rows.

**R3-P2 (per-row mutations) — PASS on B3, FAIL on the cascade.**
- B3 class (a): re-raising at the allowance conversion seam reddens exactly
  `test_rederive_malformed_evaluation_rate_returns_integrity_marker_and_cascade`
  (1 failed / 64 passed).
- B3 classes (b)/(c): re-raising at the term-amounts conversion seam reddens exactly
  the two malformed-term rows (2 failed / 63 passed).
- **S5 cascade: see finding S6.** Deleting the clause leaves **65/65 green**, and the
  handoff's declared inversion reddens a different row than claimed.

**Critical regression check (not asked for, but the thing most likely to have broken).**
The new defensive perimeter catches `(AttributeError, TypeError, ValidationError,
ArithmeticError)` and **deliberately excludes `AssertionError`** — so the C7 closed-set
tripwire, which patches raising properties over the three FKs and two episode
snapshots, still bites through the catch-all. Re-running the FK-read mutation reddens
`test_rederive_uses_unsaved_orm_instances_and_only_the_closed_snapshot_fields`. Had the
refactor used a broader `except Exception`, the phase's closed-set guarantee would have
lost its arbiter silently. It did not. Worth recording as settled ground.

**R3-P3 (S4) — PASS.** The swapped fixture
`calculate_percent_consumed(Decimal("0.01"), Decimal("100000.00"))` is present in
**both** C9 tuples (baseline and hostile). Removing `calculate_percent_consumed`'s
`localcontext()` wrapper now reddens the row (1 failed / 64 passed) where in r2 the
same mutation left 59/59 green. r2's counterfactual is the shipped fixture.

**R3-P4 (S5 payloads) — PASS on the four field branches.** Each of
`cost_per_worker_minute_minor_snapshot`, `term[<name>].amount_minor`,
`production_budget_minor` and `allowed_worker_minutes` has a row asserting the exact
payload dict. Sampled liveness: corrupting the `production_budget_minor` field label
reddens exactly its row; corrupting the `term[...]` label reddens exactly its row. The
cascade row does assert the exact two-entry field list — but see S6 for why that is not
sufficient.

**Suite — PASS.** `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app`:
**1749 passed / 23 failed / 1 deselected** in 57s, exactly +6 over r2's 1743. Focused
suite **65 passed**. Zero connectivity noise. The 23 failure IDs `diff` **empty**
against the phase-1 routed list; N14's Shopify flake did not fire. `ruff check` on both
files: clean.

**Archgraph (closing protocol step 2) — unchanged, read-only.** `archgraph_status`
only: revision `671fd92a560fbaffda67e74f21eff8128c55cacfae807d98ab27fdf6e586319b`,
126 nodes / 161 edges, **1 pending item** (the held `domain-item-economics` node), zero
diagnostics, zero stale nodes. **Zero delta from the fix**, as declared. Nothing
promoted, rejected, edited, deprecated or removed. Card 3 stands: re-anchor and
adjudicate once, after approval.

## Findings

### Should-fix

**S6 — the pinned rate→allowance cascade has no live arbiter.** R10-1 pins it
explicitly: "**Cascade pinned:** a mismatched stored rate **also** yields a derived
`allowed_worker_minutes` entry (the allowance re-derives from the rate) — both entries
are reported, by design." It is implemented as the `or rate != stored_rate` clause at
`calculator.py:533`.

**Deleting that clause leaves 65/65 green.** The cascade row's fixture uses
`cost_per_worker_minute_minor_snapshot = Decimal("399.0000")`, and at that rate the
allowance re-derives to `5.43` against a stored `5.42` — so the second entry appears
for the *ordinary* disagreement reason, and the pinned clause is never the reason the
expectation holds. That is charter **rule 2's sole-predicate companion** (a fixture
satisfying two independent sufficient causes cannot fail when one breaks), the same
shape as phase-2 **B5**. It matters practically because the clause *looks* redundant:
the obvious "cleanup" is to delete it, and nothing would catch that the owner's pinned
behaviour had disappeared.

**Verified correction (end-to-end):** in
`test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload`, set the
fixture's stored rate to `Decimal("399.5000")` and its expected allowance entry to
`rederived_value = stored_value = Decimal("5.42")`. At `399.5000` the allowance still
re-derives to `5.42`, so the entry can only come from the cascade clause. Measured:
fixture swapped + clause intact → **65 passed**; fixture swapped + clause deleted →
**1 failed, exactly `test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload`**.
(For the record: `399.9000` and `399.5000` both work; `399.0000` and `401.0000` do not.)

**Related declaration defect — this is how the gap survived.** The fix-r3 handoff and
its Review-log entry both state: "S5 invert the rate-cascade condition →
`test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload` red." Re-run
independently, the `and` inversion reddens
`test_rederive_reports_allowed_worker_minutes_mismatch_payload` — the plain allowance
row, which fails because its rate *matches* — **not** the cascade row. A
plausible-but-wrong row name converted an unguarded clause into an apparently-verified
one.

### Notes

- **N12** — `term_row.name` (`calculator.py:487`, inside the mismatch-append f-string)
  is the single attribute read left outside a `try`; a term object lacking the
  attribute raises `AttributeError` out of `rederive`. **Not an R10-1 violation** (that
  contract names `ValidationError`) and **unreachable for real rows** — `name` is NOT
  NULL and an ORM instance always carries the attribute, so only a duck-typed object
  can trigger it. Recorded as the one asymmetry in an otherwise total defensive
  perimeter. → next touch.
- **N13** — dead branching at `calculator.py:472-477`: two
  `if str(error).startswith(...)` tests guard three **identical**
  `return marker(mismatches, "term_snapshot", error)` statements. It reads as if it
  discriminates between error identities; it does not. → next touch.
- **N14** — the payload shape is **heterogeneous**: converted-exception entries carry an
  extra `"error"` key that plain value-disagreement entries lack, so a caller doing
  `entry["error"]` raises `KeyError` on half the entries. R10-1 pins no shape. → pin it
  (e.g. always include `"error": None`), or phases 7/8 key defensively.
- **N15** — the broad `except (AttributeError, TypeError, …)` also converts **programmer**
  errors into data-integrity markers: a future caller passing a wrong-typed object is
  told "the data is corrupt" instead of getting the `TypeError` that §6A.1 deliberately
  reserves for that case. R10-1 asked for totality *including* "missing snapshot
  field", so this is the chosen trade-off, not a defect — but phases 7/8 must not treat
  the marker as proof of data corruption when escalating. → phase 7/8.
- **N16** (test fidelity) — `test_rederive_malformed_purchase_snapshot_returns_integrity_marker`
  (`test_calculator.py:509`) passes a `SimpleNamespace` from `_term()` into `rederive`,
  while the other five new rederive rows use `ItemCostEvaluationTerm`. C7 pins ORM
  instances and charter rule 3 requires the object type production holds. One-line fix
  — bundle with S6 since a cycle is happening anyway.

## Lessons for the plans

- **L7** — a criterion pinning an **implication** ("X also implies Y") needs a fixture in
  which Y would **not** otherwise fire. Otherwise the row passes for the ordinary
  reason and the pin has no arbiter. Extends charter rule 2's sole-predicate companion
  from equality rows to cascade/implication pins. (Earned: S6.)
- **L8** — extending L6: a mutation declaration must be checked **against the run that
  produced it**. Naming a plausible-but-wrong row is worse than naming none, because it
  converts an unguarded clause into an apparently-verified one. Fix prompts should ask
  for the observed failing node id, not a prose description. (Earned: S6's declaration
  defect.)

## Carry-forward dispositions

Not applicable — CHANGES_REQUESTED, so nothing is carried past an approval. Routing
intent: **S6 + N16** → one small fix cycle r4 (two-line fixture change + one object-type
swap; the correction is verified above, so no exploration is needed); N12, N13 → next
touch; N14 → pin the payload shape or route to phases 7/8; N15 → phase 7/8 caller
guidance; L7, L8 → master plan §9 beside P-I. Unchanged from earlier rounds: r1's N7 →
phase 4/5 wiring arbiter; r2's N8 (the `__all__` count is 19, not 20) → coordinator
prose correction; r2's N9/N10/N11 → next touch; card 3 graph node still held.

## Mutation-probe declaration

All probing was done in a **disposable git worktree** at `8908619`
(`git worktree add --detach`), never in the main tree.

- `app/beyo_manager/domain/item_economics/calculator.py` — 10 mutations applied and
  reverted (two conversion-seam re-raises; cascade-clause deletion; cascade-clause
  inversion; `calculate_percent_consumed` wrapper removal; two field-label
  corruptions; the C7 FK-read regression probe; plus repeats for the S6 correction
  measurement). Final sha256
  `e5f42531d59c66a06e384f772f41c0971d63fa5990189f39276ff6d1d9611a49` ✓
- `app/tests/unit/domain/item_economics/test_calculator.py` — 1 mutation (the S6
  correction: cascade fixture `399.0000` → `399.5000` with its expected allowance
  entry). Final sha256
  `d7251cdeed549a1ac663253f969a994e8cce1a428815afbeeddab0690497ba30` ✓
- `__pycache__` cleared between every probe so no run could read a stale module.
- One non-source file created inside the worktree only: `app/.env`, copied from the
  main tree because it is gitignored and `conftest.py` cannot import settings without
  it. It went away with the worktree.
- Worktree removed (`git worktree remove --force`); `git worktree list` shows only the
  main tree. Main tree verified clean, both hashes unchanged.
- **Database/state side effects: none.** Every probe ran the pure unit module and
  in-memory unsaved ORM instances; no migrations, no DDL, no writes. The configured
  development database was never written to and remains at head. **Architecture graph:
  read-only** (`archgraph_status` only); revision unchanged.

## Full write perimeter

- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md`
  — appended the reviewer r3 Review log entry (append-only; all earlier entries
  untouched).
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  — phase-3 tracker row only: state `IMPLEMENTED` → `CHANGES_REQUESTED`, actor extended
  to `…; reviewer r3 (Claude)`, verdict summary appended. All prior actor stamps and
  every other row preserved verbatim.
- This handoff file, deposited after the Review-log and tracker writes.
- **No production or test code was modified.** All probe edits were made in the
  disposable worktree and reverted there before it was removed.
